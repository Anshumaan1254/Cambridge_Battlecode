#!/usr/bin/env node
// Engagements from replays: champion-vs-champion attacks/casts clustered in time (gap <= 6 rounds) and space (within 10 tiles of
// the cluster's last hit). Per engagement and side: participants (bodies that hit or were hit), their max-health sum at the start,
// deaths during it. One JSON line per engagement with >= 1 death or >= 4 hits.
//   CAMBC_CACHE=... node tools/live/engage.mjs replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
for (const file of process.argv.slice(2)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const hits = [];
  for (const e of d.events) {
    if ((e.k !== 'Attack' && e.k !== 'Cast ability') || e.who === undefined || !e.to) continue;
    const s = d.rounds[e.r - 1] || d.rounds[e.r];
    if (!s) continue;
    const t = s.ch.find((c) => c[7] && c[3] === e.to[0] && c[4] === e.to[1] && c[1] !== bodies[e.who].team);
    if (!t) continue;
    hits.push({ r: e.r, a: e.who, v: t[0], x: e.to[0], y: e.to[1] });
  }
  const deaths = d.events.filter((e) => e.k === 'Death' && e.who !== undefined);
  hits.sort((p, q) => p.r - q.r);
  const eng = [];
  for (const h of hits) {
    const last = eng.length ? eng[eng.length - 1] : null;
    if (last && h.r - last.r1 <= 6 && Math.max(Math.abs(h.x - last.x), Math.abs(h.y - last.y)) <= 10) {
      last.r1 = h.r; last.x = h.x; last.y = h.y; last.parts.add(h.a); last.parts.add(h.v); last.n++;
    } else eng.push({ r0: h.r, r1: h.r, x: h.x, y: h.y, parts: new Set([h.a, h.v]), n: 1, first: bodies[h.a].team });
  }
  for (const g of eng) {
    const s0 = d.rounds[Math.max(0, g.r0 - 1)];
    const side = [0, 1].map((t) => {
      const ps = [...g.parts].filter((i) => bodies[i].team === t);
      const mh = ps.reduce((acc, i) => { const c = s0.ch.find((c) => c[0] === i); return acc + (c ? c[6] : 0); }, 0);
      const hp = ps.reduce((acc, i) => { const c = s0.ch.find((c) => c[0] === i); return acc + (c ? c[5] : 0); }, 0);
      const dd = deaths.filter((e) => bodies[e.who].team === t && e.r >= g.r0 && e.r <= g.r1 + 2).length;
      return { n: ps.length, maxhp: mh, hp, deaths: dd };
    });
    if (side[0].deaths + side[1].deaths === 0 && g.n < 4) continue;
    console.log(JSON.stringify({ file: file.split('/').pop(), r0: g.r0, r1: g.r1, hits: g.n, first: g.first, s: side }));
  }
}
