#!/usr/bin/env node
// Recalls near the enemy: every recall start, the recaller's health fraction, whether an opposing champion was within D tiles, and
// the outcome within 7 rounds: completed (the body appears at its spawn alive), killed, or interrupted (still away and alive).
// Per team (the recaller's team). One JSON line per replay.   CAMBC_CACHE=... node tools/live/recall_punish.mjs D replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const D = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const s1 = d.rounds[1];
  const spawnTiles = [0, 1].map((t) => s1.ch.filter((c) => c[1] === t).map((c) => [c[3], c[4]]));
  const nearSpawn = (t, x, y) => spawnTiles[t].some(([a, b]) => Math.max(Math.abs(a - x), Math.abs(b - y)) <= 2);
  const out = { file: file.split(/[\\/]/).pop(), teams: { 0: {}, 1: {} } };
  const inc = (t, k) => { out.teams[t][k] = (out.teams[t][k] || 0) + 1; };
  const seen = new Set();
  for (const e of d.events) {
    if (e.k !== 'Recall' || e.who === undefined) continue;
    const key = `${e.who}:${e.r}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const s = d.rounds[e.r];
    if (!s) continue;
    const me = s.ch.find((c) => c[0] === e.who);
    if (!me || !me[7] || nearSpawn(me[1], me[3], me[4])) continue;
    const t = me[1];
    const foe = s.ch.some((c) => c[7] && c[1] !== t && Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4])) <= D);
    if (!foe) { inc(t, 'safe'); continue; }
    const low = me[5] < 0.5 * me[6];
    inc(t, low ? 'near_low' : 'near_high');
    let res = 'interrupted';
    for (let r = e.r + 1; r <= e.r + 7 && r < d.rounds.length; r++) {
      const c = d.rounds[r].ch.find((q) => q[0] === e.who);
      if (!c) continue;
      if (!c[7]) { res = 'killed'; break; }
      if (nearSpawn(t, c[3], c[4])) { res = 'completed'; break; }
    }
    inc(t, (low ? 'low_' : 'high_') + res);
  }
  console.log(JSON.stringify(out));
}
