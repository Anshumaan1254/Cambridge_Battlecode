#!/usr/bin/env node
// gap_g8: who kills whom and with what, from a fight dump (tools/live/fightdump.mjs format; exact per-step attribution).
// For every champion death: victim team / type, killing blow (killer type, basic attack or ability slot -> kit name), damage taken in
// the 10 rounds before by source (champion type x attack / slot, camps), stuns taken in the 5 rounds before, the victim's own damage
// dealt in those 10 rounds, and the number of distinct enemy champions that damaged it. Linked deaths (Cassi / Issac partner) are flagged.
// Plus per team: champion damage dealt by champion type and by attack / slot, over the whole game.
//   node tools/top2/gap/killers.mjs DUMP.json.gz   -> one JSON line per game
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const KIT = {
  Ryth: ['areastun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'stun'], Issac: ['reset', 'dash'],
  Stellar: ['dmg', 'aoe'], Prism: ['dmgstun', 'aoe'], Marcella: ['ereset', 'dmg'], Willow: ['heal', 'reset'], Ren: ['dmgstun', 'dash'],
  Varg: ['reset', 'shield'], Tavi: ['reset', 'dmgstun'], HeartOfRuin: ['shield', 'dashstun'],
};
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); process.exit(0); }
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const teamOf = (i) => B.get(i).team, typeOf = (i) => B.get(i).type;
const how = (x) => (x[5] === 6 ? (KIT[typeOf(x[2])] || ['s0', 's1'])[x[6]] || 's' + x[6] : x[5] === 5 ? 'attack' : 'k' + x[5]);
const deaths = [];
for (const e of d.ev) {
  if (e.k !== 'Death') continue;
  const v = e.who, t = e.team, r = e.r;
  const kb = d.dmg.find((x) => x[0] === e.q && x[3] === v);
  const src = {};
  let campDmg = 0, champDmg = 0, own = 0;
  const atk = new Set();
  for (const x of d.dmg) {
    if (x[3] !== v || x[1] < r - 10 || x[1] > r) continue;
    if (x[2] < 0) { campDmg += x[4]; continue; }
    if (x[2] === x[3]) continue; // reflect
    if (teamOf(x[2]) === t) continue;
    const k = typeOf(x[2]) + ':' + how(x);
    src[k] = (src[k] || 0) + x[4]; champDmg += x[4]; atk.add(x[2]);
  }
  for (const x of d.dmg) if (x[2] === v && x[2] !== x[3] && x[3] >= 0 && x[1] >= r - 10 && x[1] <= r && teamOf(x[3]) !== t) own += x[4];
  const stuns = d.stun.filter((s) => s[3] === v && s[1] >= r - 5 && s[1] <= r).map((s) => (s[2] >= 0 ? typeOf(s[2]) : 'camp'));
  deaths.push({ r, t, v: typeOf(v), bag: e.bag, linked: kb ? 0 : 1, by: e.by === 'camp' ? 'camp' : typeof e.by === 'number' ? typeOf(e.by) : String(e.by),
    kb: kb ? (kb[2] < 0 ? 'camp' : how(kb)) : null, kbAmt: kb ? kb[4] : null, src, campDmg, champDmg, own, natk: atk.size, stuns });
}
const dealt = { 0: {}, 1: {} };
for (const x of d.dmg) {
  if (x[2] < 0 || x[2] === x[3] || teamOf(x[2]) === teamOf(x[3])) continue;
  const k = typeOf(x[2]) + ':' + how(x);
  dealt[teamOf(x[2])][k] = (dealt[teamOf(x[2])][k] || 0) + x[4];
}
// camp damage by team (champion damage on camps), for the farming-power comparison
const campDealt = { 0: 0, 1: 0 };
for (const x of d.cdmg) campDealt[teamOf(x[2])] += x[4];
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), FR: d.meta.finalRound, deaths, dealt, campDealt }));
