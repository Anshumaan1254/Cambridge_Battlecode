// Endgame view from LEGEND_TRACE bench runs (bench.py output with a trace build as the first bot).
//   node tools/analysis/race_trace.mjs DIR...
// Per game: the first round a body saw a winning bag (WB lines: team banked + bags >= 1000), each carrier's bag
// and altar distance then (a=-1: no walkable altar, an island), the final round, and the race-state changes
// (RS lines). Summary: latency split (WB to end) for wins, and the task mix of our bodies over the last 150
// rounds of close wins vs close losses (both teams >= 800 banked at the end).
import fs from 'fs'; import path from 'path';
import { unwrapReplay } from '../replay/decode.mjs';
const TASKS = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const dirs = [];
for (const a of process.argv.slice(2).filter((x) => !x.startsWith('--'))) {
	if (fs.existsSync(path.join(a, 'manifest.txt'))) dirs.push(a);
	else for (const d of fs.readdirSync(a).sort()) if (fs.existsSync(path.join(a, d, 'manifest.txt'))) dirs.push(path.join(a, d));
}
const mix = { W: {}, L: {} }, nmix = { W: 0, L: 0 };
const lat = [], rsCount = [], rsFlips12 = [];
let islands = 0;
for (const dir of dirs) for (const f of fs.readdirSync(dir).filter((x) => /_[AB]\.json$/.test(x)).sort()) {
	const side = f.slice(-6, -5), us = side === 'A' ? 'teamA' : 'teamB', them = side === 'A' ? 'teamB' : 'teamA';
	const st = JSON.parse(fs.readFileSync(path.join(dir, f)));
	const won = st.match.outcome === us, R = st.match.roundsCompleted;
	const sub = { us: 0, them: 0 };
	for (const t of st.teams) sub[t.team === us ? 'us' : 'them'] = +t.submittedGems;
	const rp = path.join(dir, f.replace(/\.json$/, '.repl26a'));
	if (!fs.existsSync(rp)) continue;
	const text = unwrapReplay(fs.readFileSync(rp), side === 'A' ? 'team-a.stdout' : 'team-b.stdout').toString('latin1').replace(/\x00/g, '');
	const wb = {}; let wb0 = null; let rs = 0, flips = 0; const last = {};
	const close = Math.min(sub.us, sub.them) >= 800;
	const m = mix[won ? 'W' : 'L'];
	for (const l of text.split('\n')) {
		let x = l.match(/^WB r=(\d+) (\d+) gems=(\d+) a=(-?\d+) dist=(\d+)/);
		if (x) { const r = +x[1]; if (wb0 === null) wb0 = r; if (!wb[x[2]]) wb[x[2]] = { r, gems: +x[3], a: +x[4], dist: +x[5] }; continue; }
		x = l.match(/^RS r=(\d+) (\d+) (\d+)->(\d+)/);
		if (x) { rs++; if ((x[3] === '1' && x[4] === '2') || (x[3] === '2' && x[4] === '1')) flips++; continue; }
		x = l.match(/^T r=(\d+) (\d+) task=(\d+)/);
		if (x && close && +x[1] > R - 150) { m[TASKS[+x[3]]] = (m[TASKS[+x[3]]] || 0) + 1; }
	}
	if (close) nmix[won ? 'W' : 'L']++;
	rsCount.push(rs); rsFlips12.push(flips);
	const isl = Object.values(wb).some((b) => b.a < 0);
	islands += isl;
	if (wb0 !== null && won) lat.push(R - wb0);
	if (wb0 !== null && (process.argv.includes('--games')))
		console.log(`${f.slice(0, -5)} ${won ? 'W' : 'L'} R${R} ${sub.us}-${sub.them} WB@${wb0} lat ${R - wb0} | ${Object.entries(wb).map(([k, b]) => `${k}:r${b.r} ${b.gems}g d${b.a < 0 ? 'ISL' : b.dist}`).join(' ')} | RS ${rs} (1<->2 ${flips})`);
}
const s = (a) => a.length ? `mean ${(a.reduce((x, y) => x + y, 0) / a.length).toFixed(1)} median ${[...a].sort((x, y) => x - y)[a.length >> 1]}` : '-';
console.log(`win latency from the first winning-bag turn: n=${lat.length} ${s(lat)}; games with an island winning bag ${islands}`);
console.log(`race-state changes per game (all bodies): ${s(rsCount)}; 1<->2 flips ${s(rsFlips12)}`);
for (const k of ['W', 'L']) {
	const tot = Object.values(mix[k]).reduce((a, b) => a + b, 0) || 1;
	console.log(`close ${k} (${nmix[k]} games) last-150 task mix: ` + TASKS.map((t) => `${t} ${(100 * (mix[k][t] || 0) / tot).toFixed(1)}%`).join(' ') + ` | alive body-turns/game ${(tot / Math.max(1, nmix[k])).toFixed(0)}`);
}
