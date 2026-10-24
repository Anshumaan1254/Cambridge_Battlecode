#!/usr/bin/env node
// Routing opportunities: for every capture (CaptureGems event), who took it and how far the team's gold-bonus bodies (Vesper Vale:
// +33% gold; Marcella: 2 gold per banked gem) were from the capture tile at that moment (Chebyshev; -1 = dead or not drafted).
// One JSON line per replay:  CAMBC_CACHE=... node tools/live/res_routeopp.mjs replay...   (or through tools/live/par.py)
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';

const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
for (const file of process.argv.slice(2)) {
  let d;
  try {
    d = await decode(fs.readFileSync(file), { every: 1 });
  } catch (e) {
    console.error(file, e.message);
    continue;
  }
  const R = new Map(d.rounds.map((s) => [s.r, s]));
  const snap = (r) => { for (let k = r; k >= 0; --k) if (R.has(k)) return R.get(k); return d.rounds[0]; };
  const bodies = d.meta.bodies;
  const caps = [];
  for (const e of d.events) {
    if (e.k !== 'CaptureGems') continue;
    const s = snap(e.r);
    const near = {};
    for (const b of bodies) {
      if (b.team !== e.team || b.index === e.who) continue;
      if (b.type !== 'VesperVale' && b.type !== 'Marcella') continue;
      const c = s.ch.find((q) => q[0] === b.index);
      near[b.type] = c && c[7] ? cheb([c[3], c[4]], e.at) : -1;
    }
    // other allies standing within 1 of the capturer (bodies that waited on the capture)
    let waiting = 0;
    for (const c of s.ch) if (c[1] === e.team && c[0] !== e.who && c[7] && cheb([c[3], c[4]], e.at) <= 1) waiting += 1;
    caps.push([e.r, e.team, e.champ, e.gems, e.gold, near.VesperVale ?? null, near.Marcella ?? null, waiting]);
  }
  console.log(JSON.stringify({ file: file.split(/[\\/]/).pop(), drafts: d.meta.drafts, final: d.meta.finalRound, caps }));
}
