#!/usr/bin/env node
// Home trips in the opening from tools/live/fightdump.mjs dumps: every arrival on the own spawn while alive (from > 2 tiles away,
// rounds <= R): gold held the round before, bag carried, health share, max HP gained by 3 rounds later (purchases), whether the
// arrival happened in the round of the body's own capture (recall channelled during the capture timer). One JSON line per dump.
//   node tools/top2/opening/open_homes.mjs R dump.json.gz...
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const [Rs, ...files] = process.argv.slice(2);
const R = +Rs || 300;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
for (const file of files) {
  let d; try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { continue; }
  const S = []; for (const row of d.R) S[row[0]] = row;
  const team = new Map(d.meta.bodies.map((b) => [b.index, b.team])), type = new Map(d.meta.bodies.map((b) => [b.index, b.type]));
  const start = d.R[0][3];
  const spawn = [0, 1].map((t) => start.filter((c) => team.get(c[0]) === t).map((c) => [c[1], c[2]]));
  const capR = new Set(d.ev.filter((e) => e.k === 'CaptureGems').map((e) => e.who * 10000 + e.r));
  const out = [];
  for (let r = 2; r <= Math.min(R, d.meta.finalRound - 3); ++r) {
    const a = S[r - 1], b = S[r]; if (!a || !b) continue;
    for (const c of b[3]) {
      const t = team.get(c[0]);
      if (!c[5] || !spawn[t].some((s) => s[0] === c[1] && s[1] === c[2])) continue;
      const p = a[3].find((x) => x[0] === c[0]); if (!p || !p[5]) continue;
      if (Math.min(...spawn[t].map((s) => cheb([p[1], p[2]], s))) <= 2) continue;
      const q = S[r + 3] && S[r + 3][3].find((x) => x[0] === c[0]);
      out.push({ r, b: c[0], t, type: type.get(c[0]), gold: p[7], bag: p[6], hp: +(p[3] / p[4]).toFixed(2), hpGain: q ? q[4] - p[4] : 0,
        goldAfter: q ? q[7] : null, capRecall: capR.has(c[0] * 10000 + r) });
    }
  }
  console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), homes: out }));
}
