// Timeline near an objective: per round in [from,to], bodies within R of (cx,cy) with hp, plus the cluster hp and events.
//   node objtl.mjs REPLAY cx cy from to [R]
import fs from 'fs';
import { decode, CHAMP } from '../replay/decode.mjs';
const [f, cx, cy, from, to, RR] = process.argv.slice(2);
const R = +(RR || 8);
const d = await decode(fs.readFileSync(f), { every: 1 });
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const cidx = d.meta.camps.map((c, i) => [c, i]).filter(([c]) => cheb([c.x, c.y], [+cx, +cy]) <= 3).map(([, i]) => i);
for (const r of d.rounds) {
  if (r.r < +from || r.r > +to) continue;
  const hp = cidx.reduce((s, i) => s + r.campHp[i], 0);
  const bodies = r.ch.filter((c) => c[7] && cheb([c[3], c[4]], [+cx, +cy]) <= R).map((c) => `${'AB'[c[1]]}${CHAMP[c[2]].slice(0, 3)}(${c[3]},${c[4]})${c[5]}${c[8] ? ' g' + c[8] : ''}`);
  const ev = d.events.filter((e) => e.r === r.r && (e.k === 'Death' || e.k === 'CaptureGems' || e.k === 'Banked' || e.k === 'Recall') && (!e.at || cheb(e.at, [+cx, +cy]) <= R + 4)).map((e) => `${e.k}:${'AB'[e.team]}${e.champ}${e.gems ? ' ' + e.gems : ''}`);
  console.log(`r${r.r} hp${hp} ${bodies.join(' ')} ${ev.length ? '| ' + ev.join(' ') : ''}`);
}
