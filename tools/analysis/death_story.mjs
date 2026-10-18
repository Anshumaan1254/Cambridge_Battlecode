// The rounds before each death of one team (agent `survive`, session 6): what the victim did, who was near.
//   node tools/analysis/death_story.mjs REPLAY... [--team 1] [--back 10] [--maps a,b] [--max N] [--sum]
// Per death: one line per round (r-back .. r): victim pos/hp/bag, its actions (M move, A attack champ, a attack camp,
// C cast, R recall, S submit, H shop), enemies within 10 (type:dist:hp) and allies within 10 (type:dist:hp).
// --sum: only the summary of mechanisms per death:
//   seen      rounds between the first round an enemy that ends within 6 was within 8 of the victim and the death
//   closing   the victim's own moves in the last 'seen' rounds: toward the nearest enemy / away / none
//   farm      the victim attacked a camp in the 5 rounds before
//   flee      the victim moved away from the nearest enemy in the last 3 rounds
//   recall    the victim started a recall in the last 6 rounds
//   group     max enemies within 6 of the victim in the last 3 rounds
import fs from 'fs';
import path from 'path';
import { decode, CHAMP } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const opt = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const T0 = Number(opt('--team', 0));
const BACK = Number(opt('--back', 10));
const MAX = Number(opt('--max', 1e9));
const SUM = args.includes('--sum');
const ONLY = args.includes('--maps') ? new Set(opt('--maps').split(',')) : null;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const cnt = {};
const add = (k, v) => { cnt[k] = cnt[k] || {}; cnt[k][v] = (cnt[k][v] || 0) + 1; };
let n = 0;
for (const f of args.filter((a) => a.endsWith('.repl26a'))) {
	const base = path.basename(f, '.repl26a');
	if (ONLY && !ONLY.has(base.replace(/_[AB]$/, ''))) continue;
	// bench naming: X_B.repl26a = we are team B unless --team is given explicitly
	const T = args.includes('--team') ? T0 : base.endsWith('_B') ? 1 : 0;
	const d = await decode(fs.readFileSync(f), { every: 1 });
	const byR = new Map(d.rounds.map((r) => [r.r, r]));
	const acts = new Map();
	for (const e of d.events) {
		if (e.who === undefined || e.team !== T) continue;
		const k = `${e.r}:${e.who}`;
		let c = '';
		if (e.k === 'Move') c = 'M';
		else if (e.k === 'Attack') c = 'A';
		else if (e.k === 'Cast ability') c = 'C';
		else if (e.k === 'Recall') c = 'R';
		else if (e.k === 'Submit gems') c = 'S';
		else if (e.k === 'Shop') c = 'H';
		else continue;
		acts.set(k, (acts.get(k) || '') + c);
	}
	// camp vs champion attacks: attack target tile has a champion of the other team?
	for (const e of d.events) {
		if (e.k !== 'Attack' || e.team !== T || !e.to) continue;
		const rr = byR.get(e.r - 1) || byR.get(e.r);
		if (!rr) continue;
		const champ = rr.ch.some((c) => c[1] !== T && c[7] && cheb([c[3], c[4]], e.to) <= 1);
		if (!champ) { const k = `${e.r}:${e.who}`; acts.set(k, (acts.get(k) || '').replace('A', 'a')); }
	}
	for (const e of d.events.filter((e) => e.k === 'Death' && e.team === T)) {
		if (n >= MAX) break;
		n++;
		const lines = [];
		let firstSeen = null, toward = 0, away = 0, farm = false, flee = false, recall = false, grp = 0;
		const final = byR.get(e.r - 1) || byR.get(e.r);
		const killers = final ? final.ch.filter((c) => c[1] !== T && c[7] && cheb([c[3], c[4]], final.ch[e.who].slice(3, 5)) <= 6).map((c) => c[0]) : [];
		for (let r = e.r - BACK; r <= e.r; ++r) {
			const R = byR.get(r), Rp = byR.get(r - 1);
			if (!R) continue;
			const me = R.ch[e.who];
			const p = [me[3], me[4]];
			const en = R.ch.filter((c) => c[1] !== T && c[7] && cheb([c[3], c[4]], p) <= 10).sort((a, b) => cheb([a[3], a[4]], p) - cheb([b[3], b[4]], p));
			const al = R.ch.filter((c) => c[1] === T && c[7] && c[0] !== e.who && cheb([c[3], c[4]], p) <= 10);
			const a = acts.get(`${r}:${e.who}`) || '';
			if (firstSeen === null && R.ch.some((c) => killers.includes(c[0]) && cheb([c[3], c[4]], p) <= 8)) firstSeen = r;
			if (Rp && a.includes('M')) {
				const pp = [Rp.ch[e.who][3], Rp.ch[e.who][4]];
				const ne = Rp.ch.filter((c) => c[1] !== T && c[7]).sort((x, y) => cheb([x[3], x[4]], pp) - cheb([y[3], y[4]], pp))[0];
				if (ne && cheb([ne[3], ne[4]], pp) <= 9) {
					const dd = cheb([ne[3], ne[4]], p) - cheb([ne[3], ne[4]], pp);
					if (firstSeen !== null) { if (dd < 0) toward++; else if (dd > 0) away++; }
					if (r >= e.r - 3 && dd > 0) flee = true;
				}
			}
			if (r >= e.r - 5 && a.includes('a')) farm = true;
			if (r >= e.r - 6 && a.includes('R')) recall = true;
			if (r >= e.r - 3) grp = Math.max(grp, en.filter((c) => cheb([c[3], c[4]], p) <= 6).length);
			lines.push(`  r${r} (${p}) hp ${me[5]}/${me[6]} bag ${me[8]} [${a}] en: ${en.map((c) => `${CHAMP[c[2]]}:${cheb([c[3], c[4]], p)}:${c[5]}`).join(' ')} | al: ${al.map((c) => `${CHAMP[c[2]]}:${cheb([c[3], c[4]], p)}:${c[5]}`).join(' ')}`);
		}
		const seen = firstSeen === null ? 'none' : e.r - firstSeen <= 1 ? '0-1' : e.r - firstSeen <= 3 ? '2-3' : e.r - firstSeen <= 6 ? '4-6' : '7+';
		add('seen', seen); add('closing', toward > away ? 'toward' : away > toward ? 'away' : 'none');
		add('farm5', farm ? 'yes' : 'no'); add('flee3', flee ? 'yes' : 'no'); add('recall6', recall ? 'yes' : 'no'); add('group3', grp >= 3 ? '3+' : String(grp));
		if (!SUM) {
			console.log(`${base} r${e.r} ${e.champ} bag ${e.bag} by ${e.by} seen ${seen} toward ${toward} away ${away}`);
			console.log(lines.join('\n'));
		}
	}
}
console.log(`deaths ${n}`);
for (const [k, v] of Object.entries(cnt)) console.log(k.padEnd(9), Object.entries(v).sort((a, b) => b[1] - a[1]).map(([a, b]) => `${a} ${b} (${(100 * b / n).toFixed(0)}%)`).join(', '));
