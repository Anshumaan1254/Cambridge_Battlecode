#!/usr/bin/env node
// Stuck time per team: rounds a living body (off its spawn) neither moved nor acted (attack, cast, capture, tribute, recall, shop,
// ward), in runs of >= 4 rounds that do NOT end in a capture (standing on a reward is legitimate), plus A-B-A oscillation rounds and
// "loops" (8+ rounds of moving with net displacement <= 2). Per team: per-body totals. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/stuck.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const act = new Map(), cap = new Map();
  for (const e of d.events) {
    if (e.who === undefined) continue;
    if (/Attack|Cast ability|Submit gems|Recall|Shop|Place ward|Consumable|Gems submitted/.test(e.k)) act.set(e.r * 64 + e.who, 1);
    if (e.k === 'CaptureGems') cap.set(e.r * 64 + e.who, 1);
  }
  const s1 = d.rounds[1];
  const spawn = [0, 1].map((t) => s1.ch.filter((c) => c[1] === t).map((c) => c[3] * 1000 + c[4]));
  const out = { file: file.split('/').pop(), teams: {} };
  const campPos = (d.meta.camps || []).map((c) => [c.x, c.y]);
  const campNear = (p) => campPos.some((c) => Math.max(Math.abs(c[0] - p[0]), Math.abs(c[1] - p[1])) <= 5);
  for (const t of [0, 1]) {
    let idle = 0, aba = 0, loop = 0, nb = 0, abaE = 0, loopE = 0, loopCamp = 0;
    const enemyNear = (r, p) => (d.rounds[r]?.ch || []).some((c) => c[7] && c[1] !== t && Math.max(Math.abs(c[3] - p[0]), Math.abs(c[4] - p[1])) <= 8);
    for (const b of bodies.filter((b) => b.team === t)) {
      nb++;
      const P = (r) => { const c = d.rounds[r]?.ch.find((c) => c[0] === b.index); return c && c[7] ? [c[3], c[4]] : null; };
      let run = 0, runStart = 0;
      const pos = [];
      for (let r = 2; r < Math.min(R, d.rounds.length); r++) {
        const p = P(r), q = P(r - 1);
        pos.push(p);
        const onSpawn = p && Math.max(...spawn[t].map((k) => Math.max(Math.abs(Math.floor(k / 1000) - p[0]), Math.abs(k % 1000 - p[1])))) <= 1;
        const still = p && q && p[0] === q[0] && p[1] === q[1] && !act.has(r * 64 + b.index) && !onSpawn;
        if (still) { if (!run) runStart = r; run++; }
        else {
          if (run >= 4) { let capd = false; for (let k = runStart; k <= r + 1; k++) if (cap.has(k * 64 + b.index)) capd = true; if (!capd) idle += run; }
          run = 0;
        }
        const p2 = P(r - 2);
        if (p && q && p2 && p[0] === p2[0] && p[1] === p2[1] && (p[0] !== q[0] || p[1] !== q[1])) { aba++; if (enemyNear(r, p)) abaE++; }
      }
      // loops: windows of 8 rounds with movement every round but net displacement <= 2
      for (let i = 8; i < pos.length; i++) {
        const a = pos[i - 8], z = pos[i];
        if (!a || !z) continue;
        let moved = true;
        for (let k = i - 7; k <= i; k++) if (!pos[k] || !pos[k - 1] || (pos[k][0] === pos[k - 1][0] && pos[k][1] === pos[k - 1][1])) moved = false;
        if (moved && Math.max(Math.abs(a[0] - z[0]), Math.abs(a[1] - z[1])) <= 2) { loop++; if (enemyNear(i + 2, z)) loopE++; else if (campNear(z)) loopCamp++; }
      }
    }
    out.teams[t] = { idle: +(idle / nb).toFixed(1), aba: +(aba / nb).toFixed(1), loop: +(loop / nb).toFixed(1), abaE: +(abaE / nb).toFixed(1), loopE: +(loopE / nb).toFixed(1), loopCamp: +(loopCamp / nb).toFixed(1) };
  }
  console.log(JSON.stringify(out));
}
