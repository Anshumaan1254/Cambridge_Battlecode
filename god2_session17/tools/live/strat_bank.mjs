#!/usr/bin/env node
// Banking profile per team from tools/live/fightdump.mjs dumps (an_strategy): first bank round, banks, gems per bank, biggest bag a
// body carried, gems lost in bags, gems still carried at the end, tribute starts that never completed, altar locks placed, and the
// gems carried at r300 / r600.   node tools/live/strat_bank.mjs dump.json.gz...  -> one JSON line per game
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
for (const file of process.argv.slice(2)) {
  let d;
  try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { continue; }
  const team = new Map(d.meta.bodies.map((b) => [b.index, b.team]));
  const out = { file: path.basename(file).replace(/\.json\.gz$/, '.repl26a'), final: d.meta.finalRound, T: {} };
  for (const t of [0, 1]) out.T[t] = { firstBank: null, banks: 0, banked: 0, maxBag: 0, maxBagR: null, lostBag: 0, carriedEnd: 0, tribStarts: 0, tribDone: 0, locks: 0, bag300: 0, bag600: 0, bigBagRounds: 0 };
  for (const e of d.ev) {
    const t = team.get(e.who); if (t === undefined) continue; const T = out.T[t];
    if (e.k === 'Banked') { T.banks++; T.banked += e.gems; if (T.firstBank === null) T.firstBank = e.r; }
    else if (e.k === 'Submit gems') T.tribStarts++;
    else if (e.k === 'Gems submitted') T.tribDone++;
    else if (e.k === 'Place altar lock') T.locks++;
    else if (e.k === 'Death') T.lostBag += e.bag || 0;
  }
  for (const R of d.R) {
    for (const c of R[3]) {
      const t = team.get(c[0]); const T = out.T[t];
      if (c[6] > T.maxBag) { T.maxBag = c[6]; T.maxBagR = R[0]; }
      if (c[5] && c[6] >= 150) T.bigBagRounds++;
    }
    if (R[0] === 300 || R[0] === 600) for (const c of R[3]) out.T[team.get(c[0])][R[0] === 300 ? 'bag300' : 'bag600'] += c[6];
  }
  const last = d.R[d.R.length - 1];
  for (const c of last[3]) out.T[team.get(c[0])].carriedEnd += c[6];
  console.log(JSON.stringify(out));
}
