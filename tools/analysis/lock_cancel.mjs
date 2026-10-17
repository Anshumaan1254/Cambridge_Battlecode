// Tributes stopped by altar locks and stuns in bench.py run directories (the first bot of the run name is "us").
//   node tools/analysis/lock_cancel.mjs [--games] DIR...
// Engine facts (session 5 probes, cambc 2.2.5): an altar lock placed on an altar where an enemy is mid-tribute
// cancels that tribute (the bag is kept, the tribute restarts from 0); a stun cancels a tribute too; damage does not.
// For each team: tributes started, tributes that landed, tributes cut by an enemy lock on that altar, by a stun
// (an enemy cast hitting the tributer is not visible here: counted as "other" = neither landed nor locked nor dead),
// tributes cut by the tributer's death, and the gems in the cut bags. Also locks placed per team and how many of
// them hit a tribute in progress, and games where the winner's last bag had been cut before.
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const argv = process.argv.slice(2);
const dirs = [];
for (const a of argv.filter((x) => !x.startsWith('--'))) {
	if (fs.existsSync(path.join(a, 'manifest.txt'))) dirs.push(a);
	else for (const d of fs.readdirSync(a).sort()) if (fs.existsSync(path.join(a, d, 'manifest.txt'))) dirs.push(path.join(a, d));
}
const key = (p) => `${p[0]},${p[1]}`;
for (const dir of dirs) {
	const S = [0, 1].map(() => ({ start: 0, landed: 0, locked: 0, died: 0, other: 0, lockedGems: 0, locks: 0, lockHits: 0, lateLocked: 0 }));
	let games = 0;
	for (const f of fs.readdirSync(dir).filter((x) => /_[AB]\.repl26a$/.test(x)).sort()) {
		const d = await decode(unwrapReplay(fs.readFileSync(path.join(dir, f))), { every: 1 });
		const T = f.endsWith('_A.repl26a') ? 0 : 1;
		const team = (t) => (t === T ? 0 : 1); // 0 = us, 1 = them
		const byR = new Map(d.rounds.map((s) => [s.r, s]));
		++games;
		const open = new Map(); // who -> {r, altar, bag, team}
		const close = (who, how, r) => {
			const o = open.get(who); if (!o) return;
			const s = S[team(o.team)];
			if (how === 'landed') s.landed++; else if (how === 'locked') { s.locked++; s.lockedGems += o.bag; if (d.meta.finalRound - r <= 100) s.lateLocked++; }
			else if (how === 'died') s.died++; else s.other++;
			open.delete(who);
		};
		for (const e of d.events) {
			if (e.k === 'Submit gems') {
				if (open.has(e.who)) close(e.who, 'other', e.r);
				const s0 = byR.get(e.r - 1); const c = s0?.ch.find((q) => q[0] === e.who);
				open.set(e.who, { r: e.r, altar: key(e.to), bag: c ? c[8] : 0, team: e.team });
				S[team(e.team)].start++;
			} else if (e.k === 'Banked') close(e.who, 'landed', e.r);
			else if (e.k === 'Death') close(e.who, 'died', e.r);
			else if (e.k === 'Place altar lock') {
				S[team(e.team)].locks++;
				let hit = false;
				for (const [w, o] of open) if (o.team !== e.team && o.altar === key(e.to)) { close(w, 'locked', e.r); hit = true; }
				if (hit) S[team(e.team)].lockHits++;
			} else if (e.who != null && open.has(e.who) && ['Move', 'Attack', 'Recall', 'Cast ability'].includes(e.k)) close(e.who, 'other', e.r);
		}
		for (const w of [...open.keys()]) close(w, 'other', d.meta.finalRound);
	}
	const fmt = (s) => `tributes ${s.start}: landed ${s.landed}, cut by enemy lock ${s.locked} (${s.lockedGems} gems; ${s.lateLocked} in the last 100 rounds), died ${s.died}, other (stun/cancel/end) ${s.other}; locks placed ${s.locks}, on a tribute ${s.lockHits}`;
	console.log(`${path.basename(dir).replace(/_\d+$/, '')} (${games} games)\n  us:   ${fmt(S[0])}\n  them: ${fmt(S[1])}`);
}
