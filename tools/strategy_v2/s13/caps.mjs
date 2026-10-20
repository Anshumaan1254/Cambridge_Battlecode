import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2]));
const names = d.meta.bodies.map(x => (x.team === 0 ? 'A' : 'B') + x.type.slice(0, 4));
const r1 = d.rounds[1].ch;
const sp = [0, 1].map(t => { const c = r1.filter(c => c[1] === t); return [c.reduce((s, x) => s + x[3], 0) / c.length, c.reduce((s, x) => s + x[4], 0) / c.length]; });
const side = (t, p) => { const da = Math.hypot(p[0] - sp[t][0], p[1] - sp[t][1]), de = Math.hypot(p[0] - sp[1 - t][0], p[1] - sp[1 - t][1]); return Math.abs(da - de) < 0.15 * (da + de) ? 'neutral' : da < de ? 'own' : 'enemy'; };
const tot = {};
for (const e of d.events) if (e.k === 'CaptureGems') {
  const t = d.meta.bodies[e.who].team; const s = side(t, e.at); const k = t + ':' + s;
  tot[k] = (tot[k] ?? 0) + e.gems;
  if (process.argv[3]) console.log(e.r, names[e.who], e.gems, JSON.stringify(e.at), s);
}
console.log('final', d.meta.outcome, d.rounds.length, 'spawns', JSON.stringify(sp), JSON.stringify(tot));
const camps = d.meta.camps.map(c => `${c.type}(${c.x},${c.y})`); console.log(camps.join(' '));
