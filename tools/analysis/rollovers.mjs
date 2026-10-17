// node rollovers.mjs REPLAY... : turn rollovers (lost turns) per team, from the engine's own step log
import fs from 'fs';
import { decode } from '../replay/decode.mjs';
for (const f of process.argv.slice(2)) {
	const d = await decode(fs.readFileSync(f), { every: 1000, rollovers: true });
	const cnt = { 0: 0, 1: 0 }, open = { 0: 0, 1: 0 };
	for (const e of d.events) if (e.k === 'Turn rollover') { cnt[e.team] = (cnt[e.team] || 0) + 1; if (e.r <= 3) open[e.team] = (open[e.team] || 0) + 1; }
	console.log(`${f.split('/').slice(-2).join('/')}: rounds ${d.meta ? '' : '?'}${d.rounds?.length ?? ''} rollovers A=${cnt[0]} (rounds 1-3: ${open[0]}) B=${cnt[1]} (rounds 1-3: ${open[1]})`);
}
