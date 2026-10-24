#!/usr/bin/env node
// Capture-recall overlap timing from tools/live/fightdump.mjs dumps: for every capture (r <= 300) after which the capturer is
// home in the same round (teleported > 2 tiles), the round it arrived on the capture tile, its Recall / Cancel channel events from
// arrival - 1 to the capture, and a histogram of (capture - arrival) and (last recall start - arrival).
//   node tools/top2/opening/open_caprecall.mjs dump.json.gz...
import fs from 'node:fs';
import zlib from 'node:zlib';
const out = [];
for (const f of process.argv.slice(2)) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
  const S = []; for (const row of d.R) S[row[0]] = row;
  const type = new Map(d.meta.bodies.map((b) => [b.index, b.type]));
  for (const e of d.ev.filter((x) => x.k === 'CaptureGems' && x.r <= 300)) {
    const b = e.who;
    const at = (r) => { const row = S[r]; return row && row[3].find((c) => c[0] === b); };
    const c1 = at(e.r), c0 = at(e.r - 1);
    if (!c1 || !c0) continue;
    const home = (c1[1] !== e.at[0] || c1[2] !== e.at[1]) && Math.max(Math.abs(c1[1] - c0[1]), Math.abs(c1[2] - c0[2])) > 2;
    if (!home) continue;
    let arr = e.r - 1;
    while (arr > 1) { const c = at(arr - 1); if (!c || c[1] !== e.at[0] || c[2] !== e.at[1]) break; arr--; }
    const rec = d.ev.filter((x) => x.k === 'Recall' && x.who === b && x.r <= e.r && x.r >= arr - 1).map((x) => x.r);
    const can = d.ev.filter((x) => x.k === 'Cancel channel' && x.who === b && x.r <= e.r && x.r >= arr).map((x) => x.r);
    out.push({ f: f.split(/[\\/]/).pop(), b, type: type.get(b), cap: e.r, arrive: arr, recalls: rec, cancels: can, gems: e.gems, gold: e.gold });
  }
}
for (const o of out) console.log(JSON.stringify(o));
const hist = (a) => { const h = {}; for (const v of a) h[v] = (h[v] || 0) + 1; return h; };
console.log(JSON.stringify({ n: out.length, capMinusArrive: hist(out.map((o) => o.cap - o.arrive)),
  lastRecallMinusArrive: hist(out.map((o) => (o.recalls.length ? o.recalls[o.recalls.length - 1] - o.arrive : null))) }));
