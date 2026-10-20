import fs from 'node:fs';
import { decode, unwrapReplay, CHAMP } from '../../replay/decode.mjs';
const [f, team, r0, r1, step] = process.argv.slice(2);
const d = await decode(unwrapReplay(fs.readFileSync(f)), { every: 1 });
const R = d.rounds;
for (let r = +r0; r <= +r1; r += +(step || 10)) {
  const s = R[r]; if (!s) continue;
  const parts = s.ch.filter(c => c[1] == +team).map(c => `${CHAMP[c[2]].slice(0,4)}(${c[3]},${c[4]})${c[7] ? '' : 'X'}${Math.round(c[5])}/${c[8]}`);
  console.log(r, s.sub.join('-'), parts.join(' '));
}
