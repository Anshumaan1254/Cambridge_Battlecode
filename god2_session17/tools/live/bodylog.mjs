#!/usr/bin/env node
// Compact per-body activity log for one team, rounds [A, B]: runs of the same activity merged:
//   walk (x,y)->(x,y) | farm G<id>[mix] | fight <enemy> | cap G<id> +gems | idle | dead | recall | bank | shop
//   CAMBC_CACHE=... node tools/live/bodylog.mjs replay TEAM A B
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const [file, T, A, B] = [process.argv[2], +process.argv[3], +process.argv[4], +process.argv[5]];
const d = await decode(fs.readFileSync(file));
const camps = d.meta.camps || [];
const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
const par = camps.map((_, i) => i);
const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(c.index)] = find(j); }
const gOf = (x, y) => { const i = at.get(x * 1000 + y); return i === undefined ? -1 : find(i); };
const mix = new Map();
for (const c of camps) { const g = find(c.index); mix.set(g, (mix.get(g) || '') + c.type[0]); }
const bodies = d.meta.bodies;
for (const b of bodies.filter((b) => b.team === T)) {
  const acts = new Map();
  for (const e of d.events) {
    if (e.who !== b.index || e.r < A || e.r > B) continue;
    let a = null;
    if (e.k === 'Attack' || e.k === 'Cast ability') {
      const g = e.to ? gOf(e.to[0], e.to[1]) : -1;
      if (g >= 0) a = `farm G${g}[${mix.get(g)}]`;
      else {
        const en = (d.rounds[e.r - 1]?.ch || []).find((c) => c[7] && c[1] !== T && e.to && c[3] === e.to[0] && c[4] === e.to[1]);
        a = en ? `fight ${bodies[en[0]].type.slice(0, 4)}` : null;
      }
    } else if (e.k === 'CaptureGems') a = `CAP G${gOf(e.at[0], e.at[1])} +${e.gems}g/${e.gold}$`;
    else if (e.k === 'Banked') a = `BANK ${e.gems}`;
    else if (e.k === 'Shop') a = 'shop';
    else if (e.k === 'Death') a = 'DIED';
    if (a && (!acts.has(e.r) || /CAP|BANK|DIED/.test(a))) acts.set(e.r, a);
  }
  const line = [];
  let cur = null, r0 = A, p0 = null;
  const flush = (r1) => { if (!cur) return; line.push(cur === 'walk' ? `${r0}-${r1} walk ${p0}->${posAt(r1)}` : `${r0}-${r1} ${cur}`); };
  const posAt = (r) => { const c = d.rounds[r]?.ch.find((c) => c[0] === b.index); return c && c[7] ? `${c[3]},${c[4]}` : 'dead'; };
  for (let r = A; r <= B; r++) {
    const c = d.rounds[r]?.ch.find((c) => c[0] === b.index);
    let a = acts.get(r);
    if (!a) a = !c || !c[7] ? 'dead' : (posAt(r) !== posAt(r - 1) ? 'walk' : 'idle');
    if (/CAP|BANK|DIED/.test(a)) { flush(r - 1); line.push(`${r} ${a}`); cur = null; continue; }
    if (a !== cur) { flush(r - 1); cur = a; r0 = r; p0 = posAt(r - 1); }
  }
  flush(B);
  console.log(`${b.type}: ` + line.join(' | '));
}
