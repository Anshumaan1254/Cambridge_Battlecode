#!/usr/bin/env node
// One game's opening as text from a tools/live/fightdump.mjs dump: every body's track every K rounds (position, zone O/M/T from
// walking distances, hp/maxHp, bag, gold), captures (group class, zone, gems, gold, capturer), banks, deaths, recall arrivals and
// champion-vs-champion engagements (first strike, local numbers within 8, deaths) up to round R.
//   node tools/top2/opening/open_story.mjs GEO.jsonl dump.json.gz R [K]
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const [geoFile, file, Rs, Ks] = process.argv.slice(2);
const R = +Rs || 150, K = +Ks || 10;
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const base = path.basename(file).replace(/\.json\.gz$/, '');
const map = base.replace(/_[0-9a-f]{8}$/, '');
let g0 = null;
for (const l of fs.readFileSync(geoFile, 'utf8').split('\n')) if (l.trim()) { const g = JSON.parse(l); if (g.map === map) g0 = g; }
const W = d.meta.width;
const S = []; for (const row of d.R) S[row[0]] = row;
const start = new Map(d.R[0][3].map((c) => [c[0], [c[1], c[2]]]));
const bodies = d.meta.bodies;
const team = new Map(bodies.map((b) => [b.index, b.team])), type = new Map(bodies.map((b) => [b.index, b.type]));
const t0 = bodies.filter((b) => b.team === 0).map((b) => start.get(b.index));
const onA = g0 ? t0.filter((p) => g0.spawnA.some((s) => s[0] === p[0] && s[1] === p[1])).length : 0;
const flip = g0 ? onA < t0.length / 2 : false;
const dist = g0 ? (flip ? [g0.dB, g0.dA] : [g0.dA, g0.dB]) : null;
const zone = (t, x, y) => {
  if (!dist) return '?';
  let a = dist[t][y * W + x], b = dist[1 - t][y * W + x];
  if (a < 0 && b < 0) return '?'; if (a < 0) return 'O'; if (b < 0) return 'O';
  const f = a / (a + b); return f < 0.4 ? 'O' : f <= 0.6 ? 'M' : 'T';
};
const camps = d.meta.camps;
const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c]));
const par = new Map(camps.map((c) => [c.index, c.index]));
const find = (i) => { while (par.get(i) !== i) i = par.get(i); return i; };
for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j) { const a = find(c.index), b = find(j.index); if (a !== b) par.set(a, b); } }
const mix = new Map(); for (const c of camps) { const g = find(c.index); const m = mix.get(g) || {}; m[c.type] = (m[c.type] || 0) + 1; mix.set(g, m); }
const mixs = (g) => Object.entries(mix.get(g) || {}).map(([k, v]) => `${v}${k[0]}`).join('');
console.log(`${base}  ${d.meta.width}x${d.meta.height}  outcome ${d.meta.outcome} (1 = team 0 won) final r${d.meta.finalRound} submitted ${d.meta.submitted}`);
for (const t of [0, 1]) console.log(`team ${t}: ` + bodies.filter((b) => b.team === t).map((b) => `${b.index}:${b.type}@${start.get(b.index)}`).join(' '));
// first camp hit per body
for (const b of bodies) {
  const h = d.cdmg.find((x) => x[2] === b.index);
  if (!h) continue;
  const c = camps.find((c) => c.index === h[3]);
  console.log(`  first hit body ${b.index} ${b.type} r${h[1]} on ${c.type}@${c.x},${c.y} group ${find(c.index)}[${mixs(find(c.index))}] zone ${zone(b.team, c.x, c.y)}`);
}
const evs = [];
for (const e of d.ev) {
  if (e.r > R) continue;
  if (e.k === 'CaptureGems') { const c = at.get(e.at[0] * 1000 + e.at[1]); evs.push([e.r, `T${e.team} CAP ${type.get(e.who)}(${e.who}) +${e.gems}g +${e.gold}$ group ${c ? find(c.index) : '?'}[${c ? mixs(find(c.index)) : ''}] at ${e.at} zone ${zone(e.team, e.at[0], e.at[1])}`]); }
  if (e.k === 'Banked') evs.push([e.r, `T${e.team} BANK ${type.get(e.who)}(${e.who}) ${e.gems} at ${e.at}`]);
  if (e.k === 'Death') evs.push([e.r, `T${e.team} DEATH ${type.get(e.who)}(${e.who}) bag ${e.bag} at ${e.at} zone ${zone(e.team, e.at[0], e.at[1])} by ${typeof e.by === 'number' ? type.get(e.by) + '(' + e.by + ')' : e.by}`]);
  if (e.k === 'Place altar lock') evs.push([e.r, `T${team.get(e.who)} LOCK ${type.get(e.who)} at ${e.to}`]);
}
// engagements
const cc = d.dmg.filter((x) => x[2] >= 0 && x[3] >= 0 && x[2] !== x[3] && team.get(x[2]) !== team.get(x[3]) && x[1] <= R);
let last = null;
const pos = (r, b) => { const row = S[r]; const c = row && row[3].find((c) => c[0] === b); return c && c[5] ? [c[1], c[2]] : null; };
for (const x of cc) {
  const p = pos(x[1] - 1, x[3]) || pos(x[1], x[3]);
  if (last && x[1] - last.r1 <= 6 && (!p || !last.p || Math.max(Math.abs(p[0] - last.p[0]), Math.abs(p[1] - last.p[1])) <= 10)) { last.r1 = x[1]; last.n++; last.dmg[team.get(x[2])] += x[4]; if (p) last.p = p; continue; }
  last = { r0: x[1], r1: x[1], p, n: 1, dmg: [0, 0], striker: x[2], victim: x[3] }; last.dmg[team.get(x[2])] += x[4];
  const row = S[Math.max(1, x[1] - 1)]; const near = [0, 0];
  if (p && row) for (const c of row[3]) if (c[5] && Math.max(Math.abs(c[1] - p[0]), Math.abs(c[2] - p[1])) <= 8) near[team.get(c[0])]++;
  last.near = near;
  evs.push([x[1], () => `FIGHT T${team.get(last0.striker)} ${type.get(last0.striker)}(${last0.striker}) strikes ${type.get(last0.victim)}(${last0.victim}) at ${last0.p} zone(striker) ${last0.p ? zone(team.get(last0.striker), last0.p[0], last0.p[1]) : '?'} near T0/T1 ${last0.near} -> r${last0.r0}-${last0.r1} dmg T0 ${last0.dmg[0]} T1 ${last0.dmg[1]}`, last]);
}
var last0;
evs.sort((a, b) => a[0] - b[0]);
console.log('events:');
for (const e of evs) { if (typeof e[1] === 'function') { last0 = e[2]; console.log(`  r${e[0]} ${e[1]()}`); } else console.log(`  r${e[0]} ${e[1]}`); }
console.log(`tracks every ${K} rounds (body: x,y zone hp/max bag gold):`);
for (let r = K; r <= Math.min(R, d.meta.finalRound); r += K) {
  const row = S[r]; if (!row) continue;
  const s = (t) => row[3].filter((c) => team.get(c[0]) === t).map((c) => c[5] ? `${c[0]}:${c[1]},${c[2]}${zone(t, c[1], c[2])} ${c[3]}/${c[4]} b${c[6]} $${c[7]}` : `${c[0]}:dead`).join(' | ');
  console.log(`r${r} sub ${row[1]}-${row[2]}\n   T0 ${s(0)}\n   T1 ${s(1)}`);
}
