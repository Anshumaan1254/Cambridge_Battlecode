#!/usr/bin/env node
// Fight walks (rounds < R): every run of travel rounds (moves / ground casts) that ends with the body hitting an enemy champion.
// For each: walk length, Chebyshev distance to the hit enemy when the walk started, whether that enemy was within 8 (own sight)
// then, and the outcome within 20 rounds after the first hit: the hit enemy died (kill), the walker died (death), both, none.
// Output per team: count, mean walk, share started out of sight, outcome counts. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/fightwalks.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const camps = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
  const pos = (r, i) => { const c = d.rounds[r]?.ch.find((c) => c[0] === i); return c && c[7] ? [c[3], c[4]] : null; };
  const enemyAt = (r, t, x, y) => (d.rounds[r]?.ch || []).find((c) => c[7] && c[1] !== t && c[3] === x && c[4] === y);
  const deaths = d.events.filter((e) => e.k === 'Death' && e.who !== undefined);
  const byBody = new Map();
  for (const e of d.events) {
    if (e.who === undefined || e.r >= R) continue;
    if (!byBody.has(e.who)) byBody.set(e.who, []);
    byBody.get(e.who).push(e);
  }
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const res = { n: 0, walk: 0, unseen: 0, kill: 0, death: 0, both: 0, none: 0 };
    for (const b of bodies.filter((b) => b.team === t)) {
      const evs = byBody.get(b.index) || [];
      const travel = new Map(); const hitAt = new Map();
      for (const e of evs) {
        if (e.k === 'Move') travel.set(e.r, 1);
        else if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) {
          if (camps.has(e.to[0] * 1000 + e.to[1])) { hitAt.set(e.r, 'camp'); continue; }
          const en = enemyAt(e.r - 1, t, e.to[0], e.to[1]) || enemyAt(e.r, t, e.to[0], e.to[1]);
          if (en) { if (!hitAt.has(e.r)) hitAt.set(e.r, en[0]); } else travel.set(e.r, 1);
        }
      }
      let run = 0, start = -1;
      for (let r = 1; r < R; r++) {
        const h = hitAt.get(r);
        if (h !== undefined) {
          if (h !== 'camp' && run >= 2) {
            res.n++; res.walk += run;
            const p0 = pos(start, b.index), e0 = pos(start, h);
            if (!p0 || !e0 || Math.max(Math.abs(p0[0] - e0[0]), Math.abs(p0[1] - e0[1])) > 8) res.unseen++;
            const k = deaths.some((x) => x.who === h && x.r >= r && x.r <= r + 20);
            const dd = deaths.some((x) => x.who === b.index && x.r >= r && x.r <= r + 20);
            res[k && dd ? 'both' : k ? 'kill' : dd ? 'death' : 'none']++;
          }
          run = 0; continue;
        }
        if (travel.has(r)) { if (!run) start = r; run++; }
      }
    }
    out.teams[t] = res;
  }
  console.log(JSON.stringify(out));
}
