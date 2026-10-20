import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const [file, a, b, step, team] = [process.argv[2], +process.argv[3], +process.argv[4], +(process.argv[5] ?? 3), +(process.argv[6] ?? 0)];
const d = await decode(fs.readFileSync(file));
const names = d.meta.bodies.map(x => x.type.slice(0, 4));
for (let i = a; i <= b; i += step) {
  const r = d.rounds[i];
  const ev = d.events.filter(e => e.r > i - step && e.r <= i && d.meta.bodies[e.who]?.team === team && /Recall|Death|Banked|CaptureGems|Shop/.test(e.k)).map(e => names[e.who] + ':' + e.k);
  console.log(i, 'sub', r.sub.join('-'), r.ch.filter(c => c[1] === team).map(c => `${names[c[0]]}(${c[3]},${c[4]})${Math.round(c[5])}${c[7] ? '' : 'X'}`).join(' '), '|', r.ch.filter(c => c[1] !== team && c[7]).map(c => `${names[c[0]]}(${c[3]},${c[4]})`).join(' '), ev.join(' '));
}
