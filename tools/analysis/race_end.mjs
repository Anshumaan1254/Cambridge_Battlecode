// Gem-race endgame audit of bench.py run directories (the first bot named in the run directory is "us").
//   node tools/analysis/race_end.mjs [--all] [--min N] [--last R] DIR...
// Picks the games we lost where our banked + carried at the end was >= --min (default 800; --all: every lost
// game) and decodes their replays. Per game: who finished and when, the round our banked + carried bags first
// reached 1000 (if ever: a "timing loss" when it was before their finish), the gems we carried at the end and what
// each carrier was doing in the last rounds, our tributes in the last --last rounds (default 150: start, bag,
// channel length), and the enemy's last tribute (start, bag, nearest alive body of ours, whether one of ours came
// within 2 tiles during the channel). A summary over all selected games follows.
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay } from '../replay/decode.mjs';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? +argv[i + 1] : d; };
const ALL = argv.includes('--all');
const MIN = opt('--min', 800), LAST = opt('--last', 150);
const dirs = [];
for (let i = 0; i < argv.length; ++i) {
	const a = argv[i];
	if (a.startsWith('--')) { if (a === '--min' || a === '--last') ++i; continue; }
	if (fs.existsSync(path.join(a, 'manifest.txt'))) dirs.push(a);
	else for (const d of fs.readdirSync(a).sort()) if (fs.existsSync(path.join(a, d, 'manifest.txt'))) dirs.push(path.join(a, d));
}
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const S = { games: 0, timing: 0, carriedEnd: 0, enemyStoppable: 0, enemyNear: 0, ourChannelEnd: 0, enemyBagSum: 0, enemyTicks: 0, margins: [], lastTribAge: [] };
for (const dir of dirs) {
	const files = fs.readdirSync(dir).filter((f) => /_[AB]\.json$/.test(f)).sort();
	for (const f of files) {
		const st = JSON.parse(fs.readFileSync(path.join(dir, f)));
		const side = f.slice(-6, -5), us = side === 'A' ? 'teamA' : 'teamB', them = side === 'A' ? 'teamB' : 'teamA';
		if (st.match.outcome === us) continue;
		let sub = 0, carry = 0;
		for (const c of st.champions) if (c.team === us) { sub += +c.metrics.submittedGems; carry += +c.metrics.gems; }
		if (!ALL && sub + carry < MIN) continue;
		const rp = path.join(dir, f.replace(/\.json$/, '.repl26a'));
		if (!fs.existsSync(rp)) continue;
		const d = await decode(unwrapReplay(fs.readFileSync(rp)), { every: 1 });
		const T = side === 'A' ? 0 : 1, E = 1 - T;
		const R = d.meta.finalRound;
		const byR = new Map(d.rounds.map((s) => [s.r, s]));
		// Round our banked + carried first reached 1000.
		let enough = null;
		for (const s of d.rounds) {
			const bag = s.ch.filter((c) => c[1] === T && c[7]).reduce((a, c) => a + c[8], 0);
			if (s.sub[T] + bag >= 1000) { enough = s.r; break; }
		}
		const last = byR.get(R) || d.rounds[d.rounds.length - 1];
		// What our carriers did in the last 8 rounds.
		const acts = {};
		for (const e of d.events) if (e.team === T && e.r > R - 8 && e.who != null) (acts[e.who] ||= new Set()).add(e.k);
		const carriers = last.ch.filter((c) => c[1] === T && c[8] > 0).map((c) => `${d.meta.bodies.find((b) => b.index === c[0])?.type}:${c[8]}${c[7] ? '' : '(dead)'}[${[...(acts[c[0]] || [])].filter((k) => k !== 'Set priority').join(',')}]`);
		const deadUs = last.ch.filter((c) => c[1] === T && !c[7]).length;
		// Tributes (Submit gems events) with the bag at that moment.
		const subsOf = (team) => d.events.filter((e) => e.team === team && e.k === 'Submit gems').map((e) => {
			const s = byR.get(e.r - 1) || byR.get(e.r);
			const c = s?.ch.find((q) => q[0] === e.who);
			const bag = c ? c[8] : 0;
			return { r: e.r, who: e.who, bag, ticks: Math.max(1, Math.ceil(bag / 10)), at: c ? [c[3], c[4]] : null, champ: e.champ };
		});
		const ours = subsOf(T).filter((s) => s.r > R - LAST);
		const theirs = subsOf(E);
		const eLast = theirs[theirs.length - 1];
		let near = null, reached = false;
		if (eLast && eLast.at) {
			const s0 = byR.get(eLast.r);
			if (s0) near = Math.min(99, ...s0.ch.filter((c) => c[1] === T && c[7]).map((c) => cheb([c[3], c[4]], eLast.at)));
			for (let r = eLast.r; r <= R; ++r) {
				const s = byR.get(r); if (!s) continue;
				if (s.ch.some((c) => c[1] === T && c[7] && cheb([c[3], c[4]], eLast.at) <= 2)) reached = true;
			}
		}
		const lastOur = ours[ours.length - 1];
		const ourBankedEnd = last.sub[T];
		S.games++;
		if (enough !== null && enough < R) S.timing++;
		S.carriedEnd += last.ch.filter((c) => c[1] === T && c[7]).reduce((a, c) => a + c[8], 0);
		if (near !== null && near <= 8) S.enemyNear++;
		if (reached) S.enemyStoppable++;
		if (eLast) { S.enemyBagSum += eLast.bag; S.enemyTicks += eLast.ticks; }
		if (lastOur && lastOur.r + lastOur.ticks > R) S.ourChannelEnd++;
		S.margins.push(1000 - ourBankedEnd);
		console.log(`${path.basename(dir).replace(/_\d+$/, '')} ${f.slice(0, -5)} R${R} banked ${ourBankedEnd}-${last.sub[E]} carried ${last.ch.filter((c) => c[1] === T && c[7]).reduce((a, c) => a + c[8], 0)} ` +
			`enough@${enough ?? '-'} dead ${deadUs} | carriers ${carriers.join(' ')}`);
		console.log(`    our tributes (last ${LAST}): ${ours.map((s) => `r${s.r} ${s.champ} ${s.bag}g/${s.ticks}t`).join(', ') || 'none'}`);
		console.log(`    their last: ${eLast ? `r${eLast.r} ${eLast.champ} ${eLast.bag}g/${eLast.ticks}t at ${eLast.at} (they had ${last.sub[E] - eLast.bag} before)` : '-'} our nearest ${near ?? '-'} reached<=2 ${reached}` +
			` | their tributes last ${LAST}: ${theirs.filter((s) => s.r > R - LAST).map((s) => `r${s.r} ${s.bag}g`).join(', ')}`);
	}
}
const n = Math.max(1, S.games);
console.log(`\nclose losses ${S.games}: timing losses (banked+carried >= 1000 before their finish) ${S.timing}; mean carried at end ${(S.carriedEnd / n).toFixed(0)}; ` +
	`our tribute still channelling at the end ${S.ourChannelEnd}; their last tribute: mean bag ${(S.enemyBagSum / n).toFixed(0)} (${(S.enemyTicks / n).toFixed(1)} turns), ` +
	`one of ours within 8 at its start ${S.enemyNear}, one of ours within 2 during it ${S.enemyStoppable}; mean gems short ${(S.margins.reduce((a, b) => a + b, 0) / n).toFixed(0)}`);
