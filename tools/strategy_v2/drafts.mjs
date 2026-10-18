import fs from 'fs';
import path from 'path';
import { decode } from '../replay/decode.mjs';
const seen = new Set();
for (const f of process.argv.slice(2)) {
	const d = await decode(fs.readFileSync(f), { every: 100000 });
	const m = d.meta;
	const mp = path.basename(f).split('-_').pop().replace('.repl26a', '');
	const key = mp + JSON.stringify(m.drafts) + m.finalRound;
	if (seen.has(key)) continue;
	seen.add(key);
	console.log(`${mp.padEnd(12)} r${m.finalRound}  US: ${m.drafts[0].join(', ').padEnd(44)} THEM: ${m.drafts[1].join(', ')}  outcome ${m.outcome}`);
}
