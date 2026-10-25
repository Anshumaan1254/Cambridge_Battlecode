// Long walks away from the altars with a big bag: per body, runs of rounds carrying >= MIN gems during which the walk distance to the
// nearest altar grows by >= 12 from its lowest value in the run; the traced tasks of those rounds.
import fs from 'node:fs';
import path from 'node:path';
const { decode, unwrapReplay } = await import('../../replay/decode.mjs');
const { mapGrid } = await import('../stuck.mjs');
const TASK = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const NAMES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'];
const dir = process.argv[2], MIN = +(process.argv[3] || 60);
function bfs(w, h, blocked, roots) {
	const d = new Int32Array(w * h).fill(1 << 20), q = new Int32Array(w * h); let qh = 0, qt = 0;
	for (const i of roots) if (d[i]) { d[i] = 0; q[qt++] = i; }
	while (qh < qt) { const i = q[qh++], x = i % w, y = (i / w) | 0;
		for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { if (!dx && !dy) continue; const nx = x + dx, ny = y + dy;
			if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue; const j = ny * w + nx; if (blocked[j] || d[j] <= d[i] + 1) continue; d[j] = d[i] + 1; q[qt++] = j; } }
	return d;
}
const out = [];
const taskTot = new Map();
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a'))) {
	const raw = fs.readFileSync(path.join(dir, f));
	const ours = /_B\.repl26a$/.test(f) ? 1 : 0;
	let text = '';
	try { text = unwrapReplay(raw, ours ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'); } catch { }
	const tr = new Map();
	for (let l of text.split('\n')) { l = l.replace(/\x00/g, '').trim(); const m = l.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+)/); if (m) tr.set(m[2] + ':' + m[1], TASK[+m[3]]); }
	const rep = unwrapReplay(raw);
	const d = await decode(rep), grid = await mapGrid(rep);
	const { w, h } = grid;
	const blocked = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) blocked[i] = grid.wall[i] | grid.hole[i] | grid.altar[i] | grid.spawn[1 - ours][i];
	const roots = []; for (let i = 0; i < w * h; i++) if (grid.altar[i]) { const x = i % w, y = (i / w) | 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const nx = x + dx, ny = y + dy; if (nx >= 0 && ny >= 0 && nx < w && ny < h && !blocked[ny * w + nx]) roots.push(ny * w + nx); } }
	const af = bfs(w, h, blocked, roots);
	for (const b of d.meta.bodies.filter((q) => q.team === ours)) {
		const ti = NAMES.indexOf(b.type);
		let run = null;
		const flush = () => { if (run && run.maxGain >= 12) out.push(run); run = null; };
		for (const s of d.rounds) {
			const c = s.ch.find((q) => q[0] === b.index); if (!c) continue;
			const alive = c[7] === 1, gems = c[8], p = [c[3], c[4]];
			if (!alive || gems < MIN || grid.spawn[ours][p[1] * w + p[0]]) { flush(); continue; }
			const dd = af[p[1] * w + p[0]];
			if (!run) run = { f, champ: b.type, r0: s.r, r1: s.r, gems, dmin: dd, maxGain: 0, tasks: new Map() };
			run.r1 = s.r; run.gems = Math.max(run.gems, gems);
			run.dmin = Math.min(run.dmin, dd); run.maxGain = Math.max(run.maxGain, dd - run.dmin);
			const t = tr.get(ti + ':' + s.r) || '?'; run.tasks.set(t, (run.tasks.get(t) || 0) + 1);
		}
		flush();
	}
}
for (const r of out) for (const [t, n] of r.tasks) taskTot.set(t, (taskTot.get(t) || 0) + n);
console.log(`runs carrying >= ${MIN} that walked >= 12 steps away from the nearest altar: ${out.length}; rounds by task:`, [...taskTot].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', '));
out.sort((a, b) => b.maxGain - a.maxGain);
for (const r of out.slice(0, 20)) console.log(`  ${r.f} ${r.champ} r${r.r0}-${r.r1} bag ${r.gems} gained ${r.maxGain} steps; tasks ${[...r.tasks].map(([k, v]) => k + ':' + v).join(' ')}`);
