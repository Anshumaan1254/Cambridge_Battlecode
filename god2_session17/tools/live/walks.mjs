#!/usr/bin/env node
// Where walking goes (rounds [A, B)): every maximal run of rounds in which a body only moved is labelled by what the body did
// next: farm (hit a camp), fight (hit a champion), bank (tribute), shop (shop at spawn), capture (stood still on a reward), died,
// recall, or none (window end). Output per team: walk rounds per body by label. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/walks.mjs A B replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const A = +process.argv[2], B = +process.argv[3];
for (const file of process.argv.slice(4)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const camps = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
  const act = new Map(); // r*64+who -> label of a non-move action
  const moved = new Set();
  for (const e of d.events) {
    if (e.who === undefined || e.r < A || e.r >= B + 40) continue;
    const key = e.r * 64 + e.who;
    let lab = null;
    if (e.k === 'Move') { moved.add(key); continue; }
    if (e.k === 'Attack' || e.k === 'Cast ability') {
      if (e.to && camps.has(e.to[0] * 1000 + e.to[1])) lab = 'farm';
      else {
        // a champion on the target tile (previous or this round) = fight; else a ground cast (dash / area) = still travelling
        const t = bodies[e.who].team;
        const onTile = (rr) => (d.rounds[rr]?.ch || []).some((c) => c[7] && c[1] !== t && e.to && c[3] === e.to[0] && c[4] === e.to[1]);
        if (e.to && (onTile(e.r - 1) || onTile(e.r))) lab = 'fight';
        else { moved.add(key); continue; }
      }
    }
    else if (e.k === 'Submit gems' || e.k === 'Banked') lab = 'bank';
    else if (e.k === 'Shop') lab = 'shop';
    else if (e.k === 'CaptureGems') lab = 'capture';
    else if (e.k === 'Death') lab = 'died';
    else if (e.k === 'Recall') lab = 'recall';
    if (lab && !act.has(key)) act.set(key, lab);
  }
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const res = { farm: 0, fight: 0, bank: 0, shop: 0, capture: 0, died: 0, recall: 0, none: 0 };
    const bs = bodies.filter((b) => b.team === t);
    for (const b of bs) {
      let run = 0;
      for (let r = A; r < B + 40; r++) {
        const key = r * 64 + b.index;
        const lab = act.get(key);
        if (lab) { if (run) { res[lab] += run; run = 0; } continue; }
        if (moved.has(key) && r < B) run++;
      }
      if (run) res.none += run;
    }
    for (const k in res) res[k] = +(res[k] / bs.length).toFixed(1);
    out.teams[t] = res;
  }
  console.log(JSON.stringify(out));
}
