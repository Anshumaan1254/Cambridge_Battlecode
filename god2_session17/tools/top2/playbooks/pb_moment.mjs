#!/usr/bin/env node
// Key-moment viewer over a tools/live/fightdump.mjs dump (no engine): rounds A..B every S rounds, every living body of both teams
// (team letter A/B, type, position, hp/max, gems) within D of (X, Y) (D = 0: all bodies), then the window's events near the box:
// captures, tribute starts / banks, deaths (bag, killer), altar locks, recalls completed are not tracked here (see pb_story.mjs).
//   node tools/top2/playbooks/pb_moment.mjs dump.json.gz A B S [X Y D]
import fs from 'node:fs';
import zlib from 'node:zlib';
const [file, As, Bs, Ss, Xs, Ys, Ds] = process.argv.slice(2);
const A = +As, B = +Bs, St = +Ss, X = +(Xs ?? 0), Y = +(Ys ?? 0), D = +(Ds ?? 0);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const bodies = d.meta.bodies;
const sh = (t) => ({ VesperVale: 'Ves', HeartOfRuin: 'HoR', Marcella: 'Mar', Vendetta: 'Vnd', Prism: 'Pri', Ryth: 'Ryt', Willow: 'Wil', Tavi: 'Tav', Cassi: 'Cas', Issac: 'Iss', Stellar: 'Ste', Varg: 'Var', Ren: 'Ren' }[t] || t);
const near = (x, y) => D <= 0 || Math.max(Math.abs(x - X), Math.abs(y - Y)) <= D;
const S = new Map(d.R.slice(1).map((r) => [r[0], r]));
for (let r = A; r <= B; r += St) {
  const row = S.get(r); if (!row) continue;
  const parts = [0, 1].map((t) => row[3].filter((c) => bodies[c[0]].team === t && c[5] && near(c[1], c[2])).map((c) => `${sh(bodies[c[0]].type)}(${c[1]},${c[2]})${c[3]}/${c[4]}${c[6] ? ' g' + c[6] : ''}${c[9] ? ' STUN' : ''}`).join(' '));
  console.log(`r${r} ${row[1]}-${row[2]} | A: ${parts[0]} | B: ${parts[1]}`);
}
for (const e of d.ev) {
  if (e.r < A || e.r > B) continue;
  const p = e.at || e.to;
  if (!['CaptureGems', 'Banked', 'Submit gems', 'Death', 'Place altar lock', 'Cancel channel'].includes(e.k)) continue;
  if (e.k === 'Cancel channel') continue;
  if (p && !near(p[0], p[1])) continue;
  const who = e.who !== undefined ? `${'AB'[bodies[e.who].team]}:${sh(bodies[e.who].type)}` : '';
  console.log(`   r${e.r} ${e.k} ${who} ${p ? '@' + p : ''} ${e.gems ?? ''}${e.bag ? ' bag ' + e.bag : ''}${typeof e.by === 'number' ? ' by ' + 'AB'[bodies[e.by].team] + ':' + sh(bodies[e.by].type) : (e.by ? ' by ' + e.by : '')}`);
}
for (const x of d.stun) if (x[1] >= A && x[1] <= B) { const a = x[2] >= 0 ? `${'AB'[bodies[x[2]].team]}:${sh(bodies[x[2]].type)}` : 'camp'; console.log(`   r${x[1]} STUN ${a} -> ${'AB'[bodies[x[3]].team]}:${sh(bodies[x[3]].type)}`); }
