#!/usr/bin/env node
// Opening captures per team: for every capture before round R, the group's camp mix, how many of the team's bodies hit that
// group in the 60 rounds before (attacks or casts on its camp tiles), the capturer, the walking distance proxy (Chebyshev from
// the team's spawn centre) and the reward. One JSON line per replay: { file, teams: { 0: [caps...], 1: [...] } }.
//   CAMBC_CACHE=... node tools/live/opening_caps.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const camps = d.meta.camps || [];
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  // groups: cardinally connected camp spawn tiles
  const par = camps.map((_, i) => i);
  const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) {
    const j = at.get((c.x + dx) * 1000 + c.y + dy);
    if (j !== undefined) par[find(c.index)] = find(j);
  }
  const gOf = (x, y) => { const i = at.get(x * 1000 + y); return i === undefined ? -1 : find(i); };
  const mix = new Map();
  for (const c of camps) { const g = find(c.index); const m = mix.get(g) || {}; m[c.type] = (m[c.type] || 0) + 1; mix.set(g, m); }
  const bodies = d.meta.bodies;
  const s1 = d.rounds[1];
  const spawn = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const hits = new Map(); // group -> [{r, who}]
  for (const e of d.events) {
    if ((e.k !== 'Attack' && e.k !== 'Cast ability') || e.who === undefined || !e.to || e.r > R) continue;
    const g = gOf(e.to[0], e.to[1]);
    if (g < 0) continue;
    if (!hits.has(g)) hits.set(g, []);
    hits.get(g).push({ r: e.r, who: e.who });
  }
  const out = { file: file.split('/').pop(), W: d.meta.width, H: d.meta.height, teams: { 0: [], 1: [] }, types: [0, 1].map((t) => bodies.filter((b) => b.team === t).map((b) => b.type)) };
  const lastCap = new Map();
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' || e.who === undefined || e.r >= R || !e.at) continue;
    const g = gOf(e.at[0], e.at[1]);
    const t = bodies[e.who].team;
    const from = Math.max(e.r - 60, lastCap.get(g) ?? -1);
    const hs = (hits.get(g) || []).filter((h) => h.r > from && h.r <= e.r);
    const mine = new Set(hs.filter((h) => bodies[h.who].team === t).map((h) => h.who));
    const theirs = new Set(hs.filter((h) => bodies[h.who].team !== t).map((h) => h.who));
    const firstHit = hs.filter((h) => bodies[h.who].team === t).reduce((a, h) => Math.min(a, h.r), 1e9);
    const key = `${g}:${e.r}`;
    if (out.teams[t].some((c) => c.key === key)) { // split reward: count once, add the share
      const c = out.teams[t].find((c) => c.key === key); c.gems += e.gems; c.gold += e.gold; c.split++; continue;
    }
    lastCap.set(g, e.r);
    const sp = spawn[t];
    out.teams[t].push({ key, r: e.r, g, mix: mix.get(g), gems: e.gems, gold: e.gold, split: 1, who: bodies[e.who].type, hitters: mine.size, enemyHitters: theirs.size,
      killRounds: firstHit < 1e9 ? e.r - firstHit : null, dist: Math.round(Math.max(Math.abs(e.at[0] - sp[0]), Math.abs(e.at[1] - sp[1]))) });
  }
  console.log(JSON.stringify(out));
}
