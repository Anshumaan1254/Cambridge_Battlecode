#!/usr/bin/env node
// Death context from replays: for every death, allies / enemies (alive) within R of the victim 1 round and 5 rounds before,
// the victim's max health vs the killers' mean max health, and the round. One JSON line per death.
//   CAMBC_CACHE=... node tools/live/deathctx.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  for (const e of d.events) {
    if (e.k !== 'Death' || e.who === undefined) continue;
    const team = d.meta.bodies[e.who].team;
    const ctx = (back) => {
      const r = d.rounds[Math.max(0, e.r - back)];
      if (!r) return null;
      const me = r.ch.find((c) => c[0] === e.who);
      if (!me || !me[7]) return null;
      let al = 0, en = 0, enMax = 0;
      for (const c of r.ch) {
        if (!c[7] || c[0] === e.who) continue;
        const dd = Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4]));
        if (dd > R) continue;
        if (c[1] === team) al++; else { en++; enMax += c[6]; }
      }
      return { al, en, myMax: me[6], enMax: en ? Math.round(enMax / en) : 0, hp: me[5] };
    };
    console.log(JSON.stringify({ file: file.split('/').pop(), r: e.r, team, champ: d.meta.bodies[e.who].type, c1: ctx(1), c5: ctx(5) }));
  }
}
