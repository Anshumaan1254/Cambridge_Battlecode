#!/usr/bin/env node
// gap_g8: farming power per body from a fight dump: champion damage dealt to camps (exact, cdmg), rounds in which the body damaged a
// camp (farm rounds), alive rounds, damage per farm round, by phase (r<300, 300-600, 600-1000, 1000+), plus camp damage TAKEN
// (dmg with a camp attacker) per farm round. One JSON line per game: bodies [{team, type, dmg[4], farm[4], alive[4], taken[4]}].
//   node tools/top2/gap/campdps.mjs DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); process.exit(0); }
const ph = (r) => (r < 300 ? 0 : r < 600 ? 1 : r < 1000 ? 2 : 3);
const bodies = new Map(d.meta.bodies.map((b) => [b.index, { i: b.index, team: b.team, type: b.type, dmg: [0, 0, 0, 0], farm: [0, 0, 0, 0], alive: [0, 0, 0, 0], taken: [0, 0, 0, 0] }]));
const fr = new Set();
for (const x of d.cdmg) { const b = bodies.get(x[2]); if (!b) continue; b.dmg[ph(x[1])] += x[4]; const k = x[2] * 100000 + x[1]; if (!fr.has(k)) { fr.add(k); b.farm[ph(x[1])]++; } }
for (const x of d.dmg) if (x[2] < 0) { const b = bodies.get(x[3]); if (b) b.taken[ph(x[1])] += x[4]; }
for (const row of d.R) { const r = row[0]; if (r < 1) continue; for (const c of row[3]) if (c[5]) { const b = bodies.get(c[0]); if (b) b.alive[ph(r)]++; } }
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), FR: d.meta.finalRound, bodies: [...bodies.values()] }));
