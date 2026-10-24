#!/usr/bin/env node
// Body-time budget per team over rounds [1, R): every living-or-dead body round labelled dead | farm (hit a camp) | fight (hit a
// champion) | oncamp (standing still on a camp tile: capturing or waiting) | walk | idle (alive, not moving, no action), plus the
// rounds spent walking while an enemy champion stood within 8 (walkNearEnemy). One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/timebudget.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const camps = d.meta.camps || [];
  const campAt = new Set(camps.map((c) => c.x * 1000 + c.y));
  const bodies = d.meta.bodies;
  const act = new Map(); // body*100000 + round -> 'farm' | 'fight'
  for (const e of d.events) {
    if (e.r >= R || e.who === undefined || (e.k !== 'Attack' && e.k !== 'Cast ability') || !e.to) continue;
    const key = e.who * 100000 + e.r;
    if (campAt.has(e.to[0] * 1000 + e.to[1])) { if (!act.has(key)) act.set(key, 'farm'); }
    else {
      const en = (d.rounds[e.r - 1]?.ch || []).find((c) => c[7] && c[1] !== bodies[e.who].team && c[3] === e.to[0] && c[4] === e.to[1]);
      if (en) act.set(key, 'fight');
    }
  }
  const out = { file: file.split(/[\\/]/).pop(), teams: { 0: {}, 1: {} } };
  for (const t of [0, 1]) for (const k of ['dead', 'farm', 'fight', 'oncamp', 'walk', 'idle', 'walkNearEnemy', 'nearE', 'nearE_farm', 'nearE_fight', 'nearE_walk', 'nearE_oncamp', 'nearE_idle', 'nearE_hpAdv']) out.teams[t][k] = 0;
  for (let r = 1; r < R && r < d.rounds.length; r++) {
    const s = d.rounds[r], p = d.rounds[r - 1];
    if (!s || !p) continue;
    for (const c of s.ch) {
      const T = out.teams[c[1]];
      if (!c[7]) { T.dead++; continue; }
      const near = s.ch.filter((q) => q[7] && q[1] !== c[1] && Math.max(Math.abs(q[3] - c[3]), Math.abs(q[4] - c[4])) <= 8);
      const a0 = act.get(c[0] * 100000 + r);
      const o = p.ch.find((q) => q[0] === c[0]);
      const moved = o && (o[3] !== c[3] || o[4] !== c[4]);
      const a = a0 || (moved ? 'walk' : campAt.has(c[3] * 1000 + c[4]) ? 'oncamp' : 'idle');
      T[a]++;
      if (a === 'walk' && near.length) T.walkNearEnemy++;
      if (near.length) {
        T.nearE++;
        T['nearE_' + a]++;
        // our side's health within 8 of this body (it included) vs theirs within 8 of it: > 1 = we are stronger here
        const mine = s.ch.filter((q) => q[7] && q[1] === c[1] && Math.max(Math.abs(q[3] - c[3]), Math.abs(q[4] - c[4])) <= 8).reduce((x, q) => x + q[5], 0);
        const theirs = near.reduce((x, q) => x + q[5], 0);
        if (mine > theirs) T.nearE_hpAdv++;
      }
    }
  }
  console.log(JSON.stringify(out));
}
