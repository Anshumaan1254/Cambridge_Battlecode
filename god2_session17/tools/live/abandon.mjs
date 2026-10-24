#!/usr/bin/env node
// Work that did not pay (rounds < R): per team, "efforts" = maximal runs of hits by that team on one camp group (gaps <= 15
// rounds). Each effort ends as: captured by the team within 30 rounds of its last hit, captured by the ENEMY (stolen), or
// abandoned (nobody captured). Also deaths before R. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/abandon.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const camps = d.meta.camps || [];
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = camps.map((_, i) => i);
  const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(c.index)] = find(j); }
  const gOf = (x, y) => { const i = at.get(x * 1000 + y); return i === undefined ? -1 : find(i); };
  const bodies = d.meta.bodies;
  const caps = []; // {r, g, team}
  for (const e of d.events) if (e.k === 'CaptureGems' && e.at && e.who !== undefined) caps.push({ r: e.r, g: gOf(e.at[0], e.at[1]), team: bodies[e.who].team });
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const hits = new Map();
    for (const e of d.events) {
      if ((e.k !== 'Attack' && e.k !== 'Cast ability') || e.who === undefined || !e.to || e.r >= R || bodies[e.who].team !== t) continue;
      const g = gOf(e.to[0], e.to[1]);
      if (g < 0) continue;
      if (!hits.has(g)) hits.set(g, []);
      hits.get(g).push(e.r);
    }
    let own = 0, stolen = 0, abandoned = 0, hitsAband = 0, hitsStolen = 0;
    for (const [g, rs] of hits) {
      rs.sort((a, b) => a - b);
      let s = 0;
      for (let k = 1; k <= rs.length; k++) {
        if (k < rs.length && rs[k] - rs[k - 1] <= 15) continue;
        const a = rs[s], b = rs[k - 1], n = k - s;
        s = k;
        if (n < 3) continue;
        const c = caps.find((c) => c.g === g && c.r >= a && c.r <= b + 30);
        if (!c) { abandoned++; hitsAband += n; } else if (c.team === t) own++; else { stolen++; hitsStolen += n; }
      }
    }
    const deaths = d.events.filter((e) => e.k === 'Death' && e.who !== undefined && e.r < R && bodies[e.who].team === t).length;
    out.teams[t] = { own, stolen, abandoned, hitsAband, hitsStolen, deaths };
  }
  console.log(JSON.stringify(out));
}
