// Context of every death of one team in replays: where (own half / middle / enemy half by walking-free Chebyshev
// distance to the two spawns' champions at round 1), health the round before, enemies / allies within 6, the
// enemies' summed max health there vs ours, and the round band. Team 0 by default (--team 1 for the other).
//   node tools/analysis/death_ctx.mjs REPLAY... [--team 1] [--list]
import fs from 'fs';
import path from 'path';
import { decode } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const T = args.includes('--team') ? Number(args[args.indexOf('--team') + 1]) : 0;
const LIST = args.includes('--list');
const cnt = {}; const add = (k, v) => { cnt[k] = cnt[k] || {}; cnt[k][v] = (cnt[k][v] || 0) + 1; };
let n = 0;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
for (const f of args.filter((a) => a.endsWith('.repl26a'))) {
	const d = await decode(fs.readFileSync(f), { every: 1 });
	const R = d.rounds;
	const spawn = [0, 1].map((t) => { const c = R[0].ch.filter((c) => c[1] === t); return [c.reduce((s, c) => s + c[3], 0) / c.length, c.reduce((s, c) => s + c[4], 0) / c.length]; });
	for (const e of d.events.filter((e) => e.k === 'Death' && e.team === T)) {
		const prev = R[Math.max(0, e.r - 2)];
		const me = prev.ch[e.who];
		const pos = [me[3], me[4]];
		const dOwn = cheb(pos, spawn[T]), dEn = cheb(pos, spawn[1 - T]);
		const where = dOwn + 4 < dEn ? 'own' : dEn + 4 < dOwn ? 'enemy' : 'middle';
		const en = prev.ch.filter((c) => c[1] !== T && c[7] && cheb([c[3], c[4]], pos) <= 6);
		const al = prev.ch.filter((c) => c[1] === T && c[7] && c[0] !== e.who && cheb([c[3], c[4]], pos) <= 6 && !((me[2] === 3 && c[2] === 4) || (me[2] === 4 && c[2] === 3)));
		const enHp = en.reduce((s, c) => s + c[5], 0), alHp = al.reduce((s, c) => s + c[5], 0) + me[5];
		const hpf = me[5] / me[6];
		n++;
		add('where', where); add('band', e.r < 100 ? 'r<100' : e.r < 250 ? 'r100-249' : e.r < 500 ? 'r250-499' : 'r500+');
		add('hp', hpf < 0.25 ? '<25%' : hpf < 0.5 ? '25-50%' : hpf < 0.75 ? '50-75%' : '75%+');
		add('enemies6', en.length >= 3 ? '3+' : String(en.length)); add('allies6', al.length >= 2 ? '2+' : String(al.length));
		add('hp_ratio', enHp === 0 ? 'no enemy' : alHp >= 1.2 * enHp ? 'we>1.2x' : alHp * 1.2 >= enHp ? 'even' : 'they>1.2x');
		add('by', e.by === 'camp' ? 'camp' : 'champ'); add('champ', e.champ);
		if (LIST) console.log(`${path.basename(f)} r${e.r} ${e.champ} ${where} hp ${me[5]}/${me[6]} bag ${e.bag} en6 ${en.length} (${en.map((c) => `${c[5]}/${c[6]}`).join(',')}) al6 ${al.length}`);
	}
}
console.log(`deaths ${n}`);
for (const [k, v] of Object.entries(cnt)) console.log(k.padEnd(9), Object.entries(v).sort((a, b) => b[1] - a[1]).map(([a, b]) => `${a} ${b} (${(100 * b / n).toFixed(0)}%)`).join(', '));
