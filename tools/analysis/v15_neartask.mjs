// GOD v15: what our bodies do with an enemy within 8 (LEGEND_TRACE builds, replays kept by tools/ledger.py --keep): per traced task
// (the T lines), how many body-rounds moved without attacking, attacked, or stood. node tools/analysis/v15_neartask.mjs DIR...
import fs from 'node:fs';
import path from 'node:path';
const { decode, unwrapReplay } = await import('../replay/decode.mjs');
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const TASK = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const tab = {}, tabFar = {};
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a'))) {
	const raw = fs.readFileSync(path.join(dir, f));
	const ours = /_B\.repl26a$/.test(f) ? 1 : 0;
	let text = '';
	try { text = unwrapReplay(raw, ours ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'); } catch { continue; }
	const tr = new Map();
	for (let l of text.split('\n')) {
		l = l.replace(/\x00/g, '').trim();
		const m = l.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+)/);
		if (m) tr.set(m[2] + ':' + m[1], +m[3]);
	}
	const d = await decode(unwrapReplay(raw));
	const B = d.meta.bodies;
	const act = new Set();
	for (const e of d.events) if (e.who !== undefined && (e.k === 'Attack' || e.k === 'Cast ability')) act.add(e.r + ':' + e.who);
	for (let r = 2; r < d.rounds.length; r++) {
		const s = d.rounds[r], p = d.rounds[r - 1];
		if (!s || !p) continue;
		const pos = new Map(s.ch.map((c) => [c[0], c])), prev = new Map(p.ch.map((c) => [c[0], c]));
		for (const c of s.ch) {
			if (c[1] !== ours || !c[7]) continue;
			let near = 99;
			for (const o of s.ch) if (o[1] !== ours && o[7]) near = Math.min(near, cheb([c[3], c[4]], [o[3], o[4]]));
			const q = prev.get(c[0]);
			const moved = q && (q[3] !== c[3] || q[4] !== c[4]);
			const a = act.has(r + ':' + c[0]);
			const typeIdx = B[c[0]] ? B[c[0]].type : c[2];
			let task = tr.get(c[2] + ':' + r);
			const key = TASK[task] ?? String(task);
			const T = near <= 8 ? tab : tabFar;
			T[key] ??= { moved: 0, hit: 0, stood: 0 };
			T[key][a ? 'hit' : moved ? 'moved' : 'stood']++;
		}
	}
}
console.log('enemy within 8:', JSON.stringify(tab));
console.log('no enemy within 8:', JSON.stringify(tabFar));
