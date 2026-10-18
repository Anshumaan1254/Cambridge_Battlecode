// usage: node tools/farm/pack_watch.mjs FILE.repl26a X,Y FROM TO [R]
// Per round: health of the camps within 1 of (X,Y) (a pack) and the champions within R (default 4) of it.
import fs from 'node:fs';
import { decode, CHAMP } from '../replay/decode.mjs';
const [f, xy, from, to, rr] = process.argv.slice(2);
const [X, Y] = xy.split(',').map(Number), R = +(rr || 4);
const d = await decode(fs.readFileSync(f));
const camps = d.meta.camps.map((c, i) => ({ ...c, i })).filter((c) => Math.max(Math.abs(c.x - X), Math.abs(c.y - Y)) <= 2);
console.log('camps', camps.map((c) => `${c.type}@${c.x},${c.y}`).join(' '));
for (const s of d.rounds) {
  if (s.r < +from || s.r > +to) continue;
  const near = s.ch.filter((c) => c[7] && Math.max(Math.abs(c[3] - X), Math.abs(c[4] - Y)) <= R).map((c) => `${c[1] ? 'B' : 'A'}:${CHAMP[c[2]]}(${c[3]},${c[4]}) ${c[5]}/${c[6]}`);
  console.log(`r${s.r} camps=${camps.map((c) => s.campHp[c.i]).join(',')} | ${near.join(' ; ')}`);
}
