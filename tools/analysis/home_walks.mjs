// Walking home instead of recalling: per team, episodes where a living body walks straight towards its own spawn
// (Chebyshev distance to the spawn centre falls every round) from >= --from tiles (default 10) until it arrives,
// with the rounds they took, and the number of recalls. A recall costs 5 rounds wherever it starts, so a walk home
// from 10+ tiles away with no enemy near is time a recall would have saved.
//   node tools/analysis/home_walks.mjs [--from N] REPLAYS_OR_DIRS...   (bench naming: NAME_A/_B = first bot on team A/B)
import fs from 'fs';
import path from 'path';
import { decode } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const from = args.includes('--from') ? Number(args[args.indexOf('--from') + 1]) : 10;
const files = [];
for (const a of args.filter((x, i) => !x.startsWith('--') && args[i - 1] !== '--from'))
	if (fs.statSync(a).isDirectory()) for (const f of fs.readdirSync(a)) { if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
	else files.push(a);
const tot = { us: { walks: 0, rounds: 0, saved: 0, recalls: 0 }, them: { walks: 0, rounds: 0, saved: 0, recalls: 0 } };
for (const f of files) {
	const d = await decode(fs.readFileSync(f), { every: 1 });
	const usTeam = /_B\.repl26a$/.test(f) ? 1 : 0;
	const first = d.rounds[0].ch;
	const spawn = [0, 1].map(t => { const c = first.filter(x => x[1] === t); return [c.reduce((s, x) => s + x[3], 0) / c.length, c.reduce((s, x) => s + x[4], 0) / c.length]; });
	const run = {};
	for (const r of d.rounds) for (const c of r.ch) {
		const [i, t, , x, y, , , alive] = c;
		const dist = alive ? Math.max(Math.abs(x - spawn[t][0]), Math.abs(y - spawn[t][1])) : -1;
		const st = run[i];
		if (st && alive && dist < st.last && dist >= st.last - 2) { st.last = dist; st.n++; if (dist <= 2) { const k = t === usTeam ? 'us' : 'them'; if (st.start >= from) { tot[k].walks++; tot[k].rounds += st.n; tot[k].saved += Math.max(0, st.n - 5); } run[i] = null; } continue; }
		run[i] = alive && dist > 2 ? { start: dist, last: dist, n: 0 } : null;
	}
	for (const e of d.events) if (e.k === 'Recall') tot[e.team === usTeam ? 'us' : 'them'].recalls++;
}
const g = Math.max(1, files.length);
for (const k of ['us', 'them']) console.log(`${k}: per game ${(tot[k].walks / g).toFixed(1)} walks home from ${from}+ tiles, ${(tot[k].rounds / g).toFixed(0)} rounds walking, ${(tot[k].saved / g).toFixed(0)} rounds a recall would save; ${(tot[k].recalls / g).toFixed(1)} recalls`);
