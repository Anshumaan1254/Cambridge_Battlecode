// Agent fight: in-reach FC turns of the traced team A: previous -> current fight decision, death within 8 rounds, enemy killed within 6 tiles / 8 rounds.
// In-reach FC turns of team A: transition (previous turn's fight -> this turn's) and death within 8 rounds.
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';
const files = process.argv.slice(2).filter(a => a.endsWith('.repl26a'));
const st = {};
const add = (k, dead, kill) => { st[k] = st[k] || [0, 0, 0]; st[k][0]++; if (dead) st[k][1]++; if (kill) st[k][2]++; };
for (const f of files) {
	const buf = fs.readFileSync(f);
	const text = unwrapReplay(buf, 'team-a.stdout').toString('latin1').replace(/\0/g, '');
	const by = new Map();
	for (const l of text.split('\n')) if (l.startsWith('FC ')) {
		const o = {}; for (const m of l.matchAll(/(\w+)=([-\d.]+)/g)) o[m[1]] = Number(m[2]);
		if (!by.has(o.ty)) by.set(o.ty, new Map()); by.get(o.ty).set(o.r, o);
	}
	const d = await decode(unwrapReplay(buf), { every: 50 });
	const deaths = d.events.filter(e => e.k === 'Death' && e.team === 0);
	const ekills = d.events.filter(e => e.k === 'Death' && e.team === 1);
	for (const [ty, m] of by) {
		const dr = deaths.filter(e => CHAMP.indexOf(e.champ) === ty).map(e => e.r);
		for (const [r, o] of m) {
			if (!o.reach) continue;
			const p = m.get(r - 1);
			const dead = dr.some(x => x > r && x <= r + 8);
			const kill = ekills.some(e => e.r > r && e.r <= r + 8 && Math.max(Math.abs(e.at[0] - o.x), Math.abs(e.at[1] - o.y)) <= 6);
			const tr = !p ? 'new' : `${p.fight}->${o.fight}`;
			const ab = o.adv < 0.5 ? 'a<.5' : o.adv < 0.8 ? 'a.5-.8' : o.adv < 1.3 ? 'a.8-1.3' : 'a1.3+';
			add(`${tr} esc=${o.esc}`, dead, kill); add(`${tr} ${ab}`, dead, kill);
			add(`fight=${o.fight} esc=${o.esc} ${ab}`, dead, kill);
		}
	}
}
for (const k of Object.keys(st).sort()) console.log(k.padEnd(28), st[k][0], 'die', (100 * st[k][1] / st[k][0]).toFixed(1) + '%', 'kill', (100 * st[k][2] / st[k][0]).toFixed(1) + '%');
