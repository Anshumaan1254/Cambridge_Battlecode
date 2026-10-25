import fs from 'node:fs';
import path from 'node:path';
const { decode, unwrapReplay } = await import('../../replay/decode.mjs');
const { mapGrid } = await import('../stuck.mjs');
const dir = process.argv[2]; const lim = +(process.argv[3] || 40);
const c = new Map(); let n = 0;
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a')).slice(0, lim)) {
	const raw = fs.readFileSync(path.join(dir, f)); const ours = /_B\.repl26a$/.test(f) ? 1 : 0;
	const rep = unwrapReplay(raw); const d = await decode(rep); const g = await mapGrid(rep);
	const campTile = new Set(d.meta.camps.map((q) => q.x + ',' + q.y));
	const byRound = new Map(d.rounds.map((r) => [r.r, r]));
	for (const e of d.events) {
		if (e.k !== 'Movement blocked' || e.team !== ours || !e.to) continue;
		n++;
		const i = e.to[1] * g.w + e.to[0];
		const s = byRound.get(e.r);
		const unit = s && s.ch.some((q) => q[7] && q[3] === e.to[0] && q[4] === e.to[1]);
		const enemy = s && s.ch.some((q) => q[7] && q[1] !== ours && q[3] === e.to[0] && q[4] === e.to[1]);
		const k = (g.bush[i] ? 'bush ' : '') + (campTile.has(e.to[0] + ',' + e.to[1]) ? 'camp-tile ' : '') + (enemy ? 'enemy-there' : unit ? 'ally-there' : 'empty-at-end');
		c.set(k, (c.get(k) || 0) + 1);
	}
}
console.log(n, [...c].sort((a, b) => b[1] - a[1]));
