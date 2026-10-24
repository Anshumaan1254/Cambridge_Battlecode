#!/usr/bin/env node
// Longest stand-stills: per living body, maximal runs of rounds at one tile off its spawn (any reason), >= MIN rounds.
// Prints team, body type, rounds, tile, health at the start / end, gems carried, whether the tile is a camp spawn tile.
//   CAMBC_CACHE=... node tools/live/longstand.mjs MIN replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const MIN = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { console.error(file, e.message); continue; }
  const camps = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
  const spawn = [0, 1].map((t) => { const s = d.rounds[1]; const b = s.ch.filter((c) => c[1] === t); return b.map((c) => [c[3], c[4]]); });
  const onSpawn = (t, x, y) => spawn[t].some(([sx, sy]) => Math.max(Math.abs(sx - x), Math.abs(sy - y)) <= 1);
  const runs = [];
  const cur = new Map();
  for (const s of d.rounds) {
    if (!s) continue;
    for (const c of s.ch) {
      const k = c[0];
      const key = `${c[3]},${c[4]}`;
      const st = cur.get(k);
      if (c[7] && st && st.key === key) { st.end = s.r; st.hp1 = c[5]; st.gems = c[8]; continue; }
      if (st && st.end - st.start + 1 >= MIN && !onSpawn(st.team, st.x, st.y)) runs.push(st);
      cur.set(k, c[7] ? { body: k, team: c[1], type: d.meta.bodies[k].type, key, x: c[3], y: c[4], start: s.r, end: s.r, hp0: c[5], hp1: c[5], max: c[6], gems: c[8] } : null);
    }
  }
  for (const st of cur.values()) if (st && st.end - st.start + 1 >= MIN && !onSpawn(st.team, st.x, st.y)) runs.push(st);
  for (const r of runs.sort((a, b) => (b.end - b.start) - (a.end - a.start)))
    console.log(JSON.stringify({ file: file.split(/[\\/]/).pop(), team: r.team, type: r.type, rounds: r.end - r.start + 1, from: r.start, at: [r.x, r.y],
      hp: `${r.hp0}->${r.hp1}/${r.max}`, gems: r.gems, campTile: camps.has(r.x * 1000 + r.y) }));
}
