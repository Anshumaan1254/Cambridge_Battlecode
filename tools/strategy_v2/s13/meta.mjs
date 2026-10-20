import fs from 'fs';
import path from 'path';
import { decode } from '../../replay/decode.mjs';
const out = [];
for (const f of process.argv.slice(2)) {
	const d = await decode(fs.readFileSync(f), { every: 100000 });
	const m = d.meta;
	out.push({ file: path.basename(f), finalRound: m.finalRound, drafts: m.drafts, outcome: m.outcome, keys: Object.keys(m), w: m.width, h: m.height, gems: m.gems ?? m.finalGems, m });
}
console.log(JSON.stringify(out.slice(0,1), null, 0).slice(0, 3000));
fs.writeFileSync(process.env.OUT, JSON.stringify(out.map(o => ({file:o.file, r:o.finalRound, drafts:o.drafts, outcome:o.outcome, sub:o.m.submitted}))));
