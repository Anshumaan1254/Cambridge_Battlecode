import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const [file, a, b] = [process.argv[2], +process.argv[3], +process.argv[4]];
const d = await decode(fs.readFileSync(file));
const names = d.meta.bodies.map(x => (x.team === 0 ? 'A' : 'B') + x.type.slice(0, 4));
for (let i = a; i <= b; i++) {
  const r = d.rounds[i];
  console.log(i, r.ch.filter(c => c[7]).map(c => `${names[c[0]]}(${c[3]},${c[4]})${Math.round(c[5])}`).join(' '));
  for (const e of d.events.filter(e => e.r === i && e.who !== undefined && /Attack|Cast|Move|Recall|Death/.test(e.k))) console.log('   ', names[e.who], e.k, JSON.stringify(e.to ?? e.at ?? ''), e.target !== undefined ? 'tgt ' + (names[e.target] ?? e.target) : '');
}
