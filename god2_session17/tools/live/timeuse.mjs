#!/usr/bin/env node
// Time use per team from replays, rounds [A, B): share of body-rounds dead / fighting champions / farming camps / walking /
// idle (capturing, channelling, waiting), recalls and shop visits per body, attacks per alive body-round.
//   CAMBC_CACHE=... node tools/live/timeuse.mjs A B US_NAME_SUBSTR_IGNORED replay...   -> one JSON line per replay
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const A = +process.argv[2], B = +process.argv[3];
for (const file of process.argv.slice(4)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { console.log(JSON.stringify({ file, err: e.message })); continue; }
  const bodies = d.meta.bodies;
  const ev = new Map(); // key round*64+who -> flags
  const champAt = new Map(); // round -> Map(posKey -> team)
  for (let i = A; i < Math.min(B, d.rounds.length); i++) {
    const m = new Map();
    for (const c of d.rounds[i].ch) if (c[7]) m.set(c[3] * 1000 + c[4], c[1]);
    champAt.set(i, m);
  }
  const res = { file, teams: {} };
  const stat = [0, 1].map(() => ({ dead: 0, fight: 0, farm: 0, move: 0, idle: 0, recall: 0, shop: 0, atk: 0, alive: 0 }));
  for (const e of d.events) {
    if (e.r < A || e.r >= B || e.who === undefined) continue;
    const key = e.r * 64 + e.who;
    const f = ev.get(key) || { fight: 0, farm: 0, move: 0 };
    const team = bodies[e.who].team;
    if (e.k === 'Attack' || e.k === 'Cast ability') {
      const prev = champAt.get(e.r - 1) || champAt.get(e.r);
      const tgtTeam = e.to && prev ? prev.get(e.to[0] * 1000 + e.to[1]) : undefined;
      if (tgtTeam !== undefined && tgtTeam !== team) f.fight = 1; else if (e.k === 'Attack') f.farm = 1; else f.farm = f.farm || 0.5;
      if (e.k === 'Attack') stat[team].atk++;
    } else if (e.k === 'Move') f.move = 1;
    else if (e.k === 'Recall') stat[team].recall++;
    else if (e.k === 'Shop') stat[team].shop++;
    ev.set(key, f);
  }
  for (let i = A; i < Math.min(B, d.rounds.length); i++) {
    for (const c of d.rounds[i].ch) {
      const team = c[1];
      if (!c[7]) { stat[team].dead++; continue; }
      stat[team].alive++;
      const f = ev.get(i * 64 + c[0]);
      if (!f) stat[team].idle++;
      else if (f.fight) stat[team].fight++;
      else if (f.farm >= 1) stat[team].farm++;
      else if (f.move) stat[team].move++;
      else if (f.farm) stat[team].farm++;
      else stat[team].idle++;
    }
  }
  for (const t of [0, 1]) {
    const s = stat[t], tot = s.alive + s.dead || 1, nb = bodies.filter((b) => b.team === t).length || 1;
    res.teams[t] = {
      dead: +(s.dead / tot).toFixed(3), fight: +(s.fight / tot).toFixed(3), farm: +(s.farm / tot).toFixed(3), move: +(s.move / tot).toFixed(3),
      idle: +(s.idle / tot).toFixed(3), recalls_per_body: +(s.recall / nb).toFixed(1), shops_per_body: +(s.shop / nb).toFixed(1), atk_per_alive: +(s.atk / (s.alive || 1)).toFixed(2),
    };
  }
  console.log(JSON.stringify(res));
}
