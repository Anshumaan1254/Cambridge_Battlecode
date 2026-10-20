import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2]));
const names = d.meta.bodies.map(b => (b.team === 0 ? 'A' : 'B') + b.type.slice(0, 4));
console.log('drafts', JSON.stringify(d.meta.drafts), 'final', d.meta.outcome, d.rounds.length);
const deaths = d.events.filter(e => /eath|died/i.test(e.k));
console.log('death kinds', [...new Set(deaths.map(e => e.k))].join(','));
for (const e of deaths.slice(0, 60)) {
  const r = d.rounds[e.r];
  const me = r?.ch.find(c => c[0] === e.who);
  const near = r ? d.rounds[Math.max(0, e.r - 1)].ch.filter(c => c[7] && c[1] !== d.meta.bodies[e.who].team && me && Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4])) <= 6).map(c => names[c[0]]).join('/') : '';
  console.log(e.r, e.k, names[e.who], JSON.stringify(e.at ?? ''), 'bag', e.gems ?? '', 'enemies<=6:', near);
}
for (const k of [100, 200, 300, 400, 500]) if (d.rounds[k]) console.log('r' + k, 'sub', d.rounds[k].sub.join('-'));
