#!/usr/bin/env node
// Captures and banks of one team with every body's position at that moment: who captures, where the others are.
//   node tools/live/caps_who.mjs replay TEAM [toRound]
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2]));
const team = +process.argv[3], to = +(process.argv[4] ?? 400);
const nm = (i) => d.meta.bodies[i].type.slice(0, 4);
for (const e of d.events) {
  if (e.r > to || e.who === undefined || d.meta.bodies[e.who].team !== team) continue;
  if (!/CaptureGems|Banked|Death|Shop/.test(e.k)) continue;
  if (e.k === 'Shop') continue;
  const s = d.rounds[e.r];
  const pos = s.ch.filter((c) => c[1] === team).map((c) => `${nm(c[0])}${c[7] ? `(${c[3]},${c[4]})` : '(dead)'}${c[0] === e.who ? '*' : ''}`).join(' ');
  console.log(`r${e.r} ${nm(e.who)} ${e.k} ${e.gems ?? e.n ?? ''} | ${pos}`);
}
