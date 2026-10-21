// node rollover_who.mjs REPLAY... : turn rollovers (lost turns) per champion and round band, from the engine's step log
import fs from 'fs';
import { decode } from '../replay/decode.mjs';
for (const f of process.argv.slice(2)) {
	const d = await decode(fs.readFileSync(f), { every: 1000, rollovers: true });
	const by = {};
	for (const e of d.events) {
		if (e.k !== 'Turn rollover' || e.r <= 3) continue;
		const who = (e.team === 0 ? 'A:' : 'B:') + (e.champ ?? '?');
		const band = e.r < 100 ? '<100' : e.r < 300 ? '100-299' : e.r < 1000 ? '300-999' : '1000+';
		by[who] = by[who] || {};
		by[who][band] = (by[who][band] || 0) + 1;
	}
	console.log(f.split('/').pop(), JSON.stringify(by));
}
