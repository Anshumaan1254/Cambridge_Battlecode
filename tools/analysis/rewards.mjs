// Uncollected rewards: how long a dead camp group's reward waits for its capture (gr=1 in the replay snapshots),
// and which team stood nearest to it meanwhile. Long waits next to our own champions are lost farming.
//   node tools/analysis/rewards.mjs REPLAY... [--min N]   (default: waits of 15+ rounds)
import fs from 'fs';
import { decode } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const min = args.includes('--min') ? Number(args[args.indexOf('--min') + 1]) : 15;
for (const f of args.filter((a, i) => a.endsWith('.repl26a'))) {
	const d = await decode(fs.readFileSync(f), { every: 1 });
	const camps = d.meta.camps || [];
	const open = {}; const waits = [];
	for (const r of d.rounds) {
		r.gr.forEach((v, g) => {
			if (v && open[g] === undefined) open[g] = r.r;
			if (!v && open[g] !== undefined) { waits.push([g, open[g], r.r]); delete open[g]; }
		});
	}
	for (const g in open) waits.push([Number(g), open[g], d.rounds.at(-1).r]);
	const long = waits.filter(([, a, b]) => b - a >= min);
	const tot = waits.reduce((s, [, a, b]) => s + b - a, 0);
	console.log(`${f.split('/').pop()}: ${waits.length} rewards, mean wait ${(tot / Math.max(1, waits.length)).toFixed(1)} rounds, ${long.length} waited ${min}+`);
	for (const [g, a, b] of long.slice(0, 12)) console.log(`   group ${g}: dead r${a} .. captured/ended r${b} (${b - a} rounds)`);
}
