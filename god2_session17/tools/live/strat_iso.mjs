#!/usr/bin/env node
// an_strategy: champion-kill deaths with allies / enemies within 6 one round before (isolated, outnumbered), per team, from
// tools/live/fightdump.mjs dumps.   node tools/live/strat_iso.mjs dump.json.gz...  -> one JSON line per game
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
for (const file of process.argv.slice(2)) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const team = new Map(d.meta.bodies.map((b) => [b.index, b.team]));
  const R = new Map(d.R.map((x) => [x[0], x[3]]));
  const out = { file: path.basename(file).replace('.json.gz', '.repl26a'), T: { 0: { d: 0, iso: 0, outnum: 0, early: 0, earlyIso: 0 }, 1: { d: 0, iso: 0, outnum: 0, early: 0, earlyIso: 0 } } };
  for (const e of d.ev) {
    if (e.k !== 'Death' || e.by === 'camp') continue;
    const t = team.get(e.who); const ch = R.get(e.r - 1); if (!ch) continue;
    const me = ch.find((c) => c[0] === e.who); if (!me || !me[5]) continue;
    let al = 0, en = 0;
    for (const c of ch) { if (!c[5] || c[0] === e.who) continue; const dd = Math.max(Math.abs(c[1] - me[1]), Math.abs(c[2] - me[2])); if (dd <= 6) { if (team.get(c[0]) === t) al++; else en++; } }
    const T = out.T[t]; T.d++; if (al === 0) T.iso++; if (en > al + 1) T.outnum++;
    if (e.r < 400) { T.early++; if (al === 0) T.earlyIso++; }
  }
  console.log(JSON.stringify(out));
}
