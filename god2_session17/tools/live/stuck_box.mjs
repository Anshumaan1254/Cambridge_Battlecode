#!/usr/bin/env node
// "Stuck in place" episodes: runs of >= L rounds in which a living body stays inside a 3x3 box, off its spawn, without capturing,
// tributing, recalling or attacking/casting at anything (moving inside the box counts). Per team: episodes and rounds per body, and
// the longest. One JSON line per replay.   CAMBC_CACHE=... node tools/live/stuck_box.mjs L replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const L = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const busy = new Set();
  for (const e of d.events) if (e.who !== undefined && /Attack|Cast ability|Submit gems|Recall|CaptureGems|Gems submitted|Shop/.test(e.k)) busy.add(e.r * 64 + e.who);
  const s1 = d.rounds[1];
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const sp = s1.ch.filter((c) => c[1] === t).map((c) => [c[3], c[4]]);
    let eps = 0, rounds = 0, longest = 0, nb = 0;
    for (const b of bodies.filter((b) => b.team === t)) {
      nb++;
      let x0 = 0, x1 = 0, y0 = 0, y1 = 0, run = 0, idleRun = 0;
      for (let r = 2; r < d.rounds.length; r++) {
        const c = d.rounds[r].ch.find((c) => c[0] === b.index);
        const alive = c && c[7];
        const onSpawn = alive && sp.some((s) => Math.max(Math.abs(s[0] - c[3]), Math.abs(s[1] - c[4])) <= 1);
        const isBusy = busy.has(r * 64 + b.index);
        const end = () => { if (idleRun >= L) { eps++; rounds += idleRun; longest = Math.max(longest, idleRun); } idleRun = 0; };
        if (!alive || onSpawn || isBusy) { end(); run = 0; continue; }
        if (run === 0) { x0 = x1 = c[3]; y0 = y1 = c[4]; run = 1; idleRun = 1; continue; }
        const nx0 = Math.min(x0, c[3]), nx1 = Math.max(x1, c[3]), ny0 = Math.min(y0, c[4]), ny1 = Math.max(y1, c[4]);
        if (nx1 - nx0 <= 2 && ny1 - ny0 <= 2) { x0 = nx0; x1 = nx1; y0 = ny0; y1 = ny1; idleRun++; }
        else { end(); x0 = x1 = c[3]; y0 = y1 = c[4]; idleRun = 1; }
      }
      if (idleRun >= L) { eps++; rounds += idleRun; longest = Math.max(longest, idleRun); }
    }
    out.teams[t] = { eps: +(eps / nb).toFixed(2), rounds: +(rounds / nb).toFixed(1), longest };
  }
  console.log(JSON.stringify(out));
}
