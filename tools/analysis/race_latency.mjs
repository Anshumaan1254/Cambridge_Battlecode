// Finish latency in bench.py run directories: for each team, the round its banked + carried gems first reached
// 1000 ("enough") and the round the game ended. For the winner, latency = final round - enough round: the time
// the last bags took to walk to an altar and channel. For the loser, whether it had enough before the winner
// finished (a timing loss) and by how many rounds the winner beat it.
//   node tools/analysis/race_latency.mjs [--comp] DIR...      (the first bot of the run name is "us")
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const argv = process.argv.slice(2);
const COMP = new Set(fs.readdirSync(path.join(path.dirname(new URL(import.meta.url).pathname), '..', '..', 'maps', 'comp')).map((f) => f.replace(/\.map26a$/, '')));
const dirs = [];
for (const a of argv.filter((x) => !x.startsWith('--'))) {
	if (fs.existsSync(path.join(a, 'manifest.txt'))) dirs.push(a);
	else for (const d of fs.readdirSync(a).sort()) if (fs.existsSync(path.join(a, d, 'manifest.txt'))) dirs.push(path.join(a, d));
}
for (const dir of dirs) {
	const lat = { us: [], them: [] }; let tl = 0, tlThem = 0, n = 0, close = 0;
	const lines = [];
	for (const f of fs.readdirSync(dir).filter((x) => /_[AB]\.repl26a$/.test(x)).sort()) {
		const name = f.slice(0, -10);
		if (argv.includes('--comp') && !COMP.has(name)) continue;
		const d = await decode(unwrapReplay(fs.readFileSync(path.join(dir, f))), { every: 1 });
		const T = f.endsWith('_A.repl26a') ? 0 : 1, E = 1 - T;
		const R = d.meta.finalRound, sub = d.meta.submitted;
		const won = sub[T] >= 1000 ? true : sub[E] >= 1000 ? false : sub[T] > sub[E];
		const enough = [null, null];
		for (const s of d.rounds) for (const t of [0, 1]) {
			if (enough[t] !== null) continue;
			const bag = s.ch.filter((c) => c[1] === t && c[7]).reduce((a, c) => a + c[8], 0);
			if (s.sub[t] + bag >= 1000) enough[t] = s.r;
		}
		++n;
		const W = won ? T : E, L = 1 - W;
		if (enough[W] !== null && sub[W] >= 1000) (won ? lat.us : lat.them).push(R - enough[W]);
		if (enough[L] !== null && enough[L] < R) { if (won) tlThem++; else tl++; }
		if (Math.min(sub[0], sub[1]) >= 850) close++;
		lines.push(`${name}_${'AB'[T]} ${won ? 'W' : 'L'} R${R} ${sub[T]}-${sub[E]} enough us@${enough[T] ?? '-'} them@${enough[E] ?? '-'}`);
	}
	const st = (a) => a.length ? `n=${a.length} mean ${(a.reduce((x, y) => x + y, 0) / a.length).toFixed(1)} median ${[...a].sort((x, y) => x - y)[a.length >> 1]}` : 'n=0';
	if (argv.includes('--games')) console.log(lines.join('\n'));
	console.log(`${path.basename(dir).replace(/_\d+$/, '')}: games ${n}, both >= 850 banked ${close}; finish latency ours ${st(lat.us)}, theirs ${st(lat.them)}; timing losses ours ${tl}, theirs ${tlThem}`);
}
