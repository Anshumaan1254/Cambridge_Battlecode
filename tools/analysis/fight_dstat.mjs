// Agent fight: deaths of the traced team A (XM_TRACE build) classified by the FC fight lines of the last 12 rounds.
//   node tools/analysis/fight_dstat.mjs REPLAY...   (SHOW=1 prints the turn before entering enemy reach)
// For every death of the traced team-A body: the FC line sequence over the last 12 rounds, classified.
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';
const files = process.argv.slice(2).filter(a => a.endsWith('.repl26a'));
const cnt = {}; const add = (k, v) => { cnt[k] = cnt[k] || {}; cnt[k][v] = (cnt[k][v] || 0) + 1; };
let n = 0;
for (const f of files) {
	const buf = fs.readFileSync(f);
	const text = unwrapReplay(buf, 'team-a.stdout').toString('latin1').replace(/\0/g, '');
	const fc = new Map();
	for (const l of text.split('\n')) if (l.startsWith('FC ')) {
		const o = {}; for (const m of l.matchAll(/(\w+)=([-\d.]+)/g)) o[m[1]] = Number(m[2]);
		fc.set(`${o.r}:${o.ty}`, o);
	}
	const d = await decode(unwrapReplay(buf), { every: 1 });
	const seenPair = new Set();
	for (const e of d.events.filter((e) => e.k === 'Death' && e.team === 0)) {
		const ty = CHAMP.indexOf(e.champ);
		const pair = e.champ === 'Cassi' || e.champ === 'Issac';
		const seq = [];
		for (let r = e.r - 12; r <= e.r; ++r) { const o = fc.get(`${r}:${ty}`); if (o) seq.push(o); }
		n++;
		add('champ', e.champ);
		if (!seq.length) { add('class', 'no FC line in 12 rounds'); continue; }
		const last = seq[seq.length - 1];
		// first in-reach line of the final contiguous stretch
		let i = seq.length - 1; while (i > 0 && seq[i - 1].reach === 1 && seq[i - 1].r === seq[i].r - 1) i--;
		const first = seq[i];
		const before = i > 0 ? seq[i - 1] : null;
		const nFight = seq.slice(i).filter(o => o.fight === 1).length, nAll = seq.length - i;
		if (process.env.SHOW && before && before.reach === 0) console.log(e.champ, "r"+e.r, "before:", JSON.stringify({r: before.r, adv: before.adv, td: before.td, ne: before.ne, na: before.na, hp: before.hp, iso: before.iso, bk: before.bk}), "first:", JSON.stringify({r: first.r, adv: first.adv, td: first.td, ne: first.ne, na: first.na, esc: first.esc, fight: first.fight}));
		add("reach_entry", first.reach === 0 ? 'never in reach' : !before ? 'already in reach (no prior line)' : before.reach === 0 ? (before.fight ? 'walked in fighting' : 'came in not fighting') : 'gap');
		add('stretch_fight_share', nFight === 0 ? 'all flee' : nFight === nAll ? 'all fight' : 'mixed');
		const flips = seq.slice(i).reduce((s, o, k, a) => s + (k > 0 && a[k - 1].fight !== o.fight ? 1 : 0), 0);
		add('flips', flips >= 2 ? '2+' : String(flips));
		add('first_adv', first.adv < 0.5 ? '<0.5' : first.adv < 0.8 ? '0.5-0.8' : first.adv < 1.3 ? '0.8-1.3' : '1.3+');
		add('first_hp', first.hp / first.mhp < 0.25 ? '<25' : first.hp / first.mhp < 0.5 ? '25-50' : first.hp / first.mhp < 0.75 ? '50-75' : '75+');
		add('last_decision', last.fight ? (last.kill ? 'fight killable' : last.reach ? (last.esc ? 'fight in reach esc' : 'fight cornered') : 'fight out of reach') : (last.reach ? (last.esc ? 'flee esc' : 'flee no-esc') : 'no fight out of reach'));
		add('first_decision', first.fight ? (first.kill ? 'fight killable' : first.reach ? (first.esc ? 'fight in reach esc' : 'fight cornered') : 'fight out of reach') : (first.reach ? (first.esc ? 'flee esc' : 'flee no-esc') : 'no fight out of reach'));
		add('first_ne', first.ne >= 3 ? '3+' : String(first.ne));
		add('stretch_len', nAll <= 2 ? '1-2' : nAll <= 5 ? '3-5' : '6+');
	}
}
console.log('deaths', n);
for (const [k, v] of Object.entries(cnt)) console.log(k.padEnd(20), Object.entries(v).sort((a, b) => b[1] - a[1]).map(([a, b]) => `${a} ${b}`).join(', '));
