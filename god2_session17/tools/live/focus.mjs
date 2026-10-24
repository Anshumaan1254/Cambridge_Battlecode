#!/usr/bin/env node
// Fight execution per engagement (champion-vs-champion hits clustered as in engage.mjs): per side, hits on champions, distinct
// targets, focus = share of hits on the most-hit target, hits that were casts (spells), stun casts, deaths, and the max-health sums
// at the start. One JSON line per engagement with >= 6 hits.   CAMBC_CACHE=... node tools/live/focus.mjs replay...
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
    hits.push({ r: e.r, a: e.who, v: t[0], x: e.to[0], y: e.to[1], cast: e.k === 'Cast ability', slot: e.slot });
  }
  const deaths = d.events.filter((e) => e.k === 'Death' && e.who !== undefined);
  hits.sort((p, q) => p.r - q.r);
  const eng = [];
  for (const h of hits) {
    const last = eng.length ? eng[eng.length - 1] : null;
    if (last && h.r - last.r1 <= 6 && Math.max(Math.abs(h.x - last.x), Math.abs(h.y - last.y)) <= 10) { last.r1 = h.r; last.x = h.x; last.y = h.y; last.h.push(h); }
    else eng.push({ r0: h.r, r1: h.r, x: h.x, y: h.y, h: [h] });
  }
  for (const g of eng) {
    if (g.h.length < 6) continue;
    const s0 = d.rounds[Math.max(0, g.r0 - 1)];
    const parts = new Set(g.h.flatMap((h) => [h.a, h.v]));
    const side = [0, 1].map((t) => {
      const mine = g.h.filter((h) => bodies[h.a].team === t);
      const tc = {};
      for (const h of mine) tc[h.v] = (tc[h.v] || 0) + 1;
      const top = Math.max(0, ...Object.values(tc));
      const ps = [...parts].filter((i) => bodies[i].team === t);
      const mh = ps.reduce((acc, i) => { const c = s0.ch.find((c) => c[0] === i); return acc + (c ? c[6] : 0); }, 0);
      const dd = deaths.filter((e) => bodies[e.who].team === t && e.r >= g.r0 && e.r <= g.r1 + 2).length;
      return { n: ps.length, hits: mine.length, targets: Object.keys(tc).length, focus: mine.length ? +(top / mine.length).toFixed(2) : null, casts: mine.filter((h) => h.cast).length, attackers: new Set(mine.map((h) => h.a)).size, maxhp: mh, deaths: dd };
    });
    console.log(JSON.stringify({ file: file.split('/').pop(), r0: g.r0, r1: g.r1, s: side }));
  }
}
