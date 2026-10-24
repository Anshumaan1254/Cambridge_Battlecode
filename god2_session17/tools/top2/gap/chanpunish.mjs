#!/usr/bin/env node
// gap_g8: channels (tributes and recalls) and whether the other side punishes them, from a fight dump.
//  tributes: every 'Submit gems' start by team t: bag at the start (bucket <50, 50-99, 100-199, 200+), outcome (done = 'Gems submitted'
//   by the body before it acts again, dead, stunned, locked = an opposing 'Place altar lock' during it, cancelled), the closest opposing
//   body during the channel, whether the other side damaged / stunned it.
//  recalls: every 'Recall' start away from the own spawn (repeats within 5 rounds skipped): nearest opposing body at the start (bucket),
//   outcome (done = on spawn within 7 rounds, dead, interrupted), whether it was hit by a champion.
// One JSON line per game with counters keyed "trib|t|bag|key" and "rec|t|near|key".   node tools/top2/gap/chanpunish.mjs DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); process.exit(0); }
const FR = d.meta.finalRound;
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const NB = Math.max(...d.meta.bodies.map((b) => b.index)) + 1;
const teamOf = (i) => B.get(i).team;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) { const row = d.R[i]; const r = row[0]; if (r < 1 || r > FR) continue; const a = new Array(NB); for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5], c[6]]; ST[r] = a; }
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));
const spawn = [0, 1].map((t) => TB[t].map((b) => P(1, b)).filter(Boolean).map((p) => [p[0], p[1]]));
const onSpawn = (t, p) => spawn[t].some((s) => cheb(s, p) <= 2);
const out = {};
const inc = (k, v = 1) => { out[k] = (out[k] || 0) + v; };
const evBy = new Map();
for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
const locks = d.ev.filter((e) => e.k === 'Place altar lock');
const nearestOpp = (r, b) => { const me = P(r, b); let m = 99; for (const e of TB[1 - teamOf(b)]) { const q = P(r, e); if (q && q[4]) m = Math.min(m, cheb(q, me)); } return m; };
for (const [b, evs] of evBy) {
  const t = teamOf(b);
  let lastRec = -99;
  for (let i = 0; i < evs.length; i++) {
    const e = evs[i];
    if (e.k === 'Submit gems') {
      const me = P(e.r - 1, b); if (!me || !me[4]) continue;
      const bag = me[5];
      const bk = bag < 50 ? 'a<50' : bag < 100 ? 'b50-99' : bag < 200 ? 'c100-199' : 'd200+';
      let end = Math.min(FR, e.r + Math.ceil(bag / 10) + 3), outc = 'cancel';
      for (let j = i + 1; j < evs.length; j++) {
        const f = evs[j];
        if (f.k === 'Gems submitted') { end = f.r; outc = 'done'; break; }
        if (f.k === 'Death') { end = f.r; outc = 'dead'; break; }
        if (f.k === 'Move' || f.k === 'Attack' || f.k === 'Cast ability' || f.k === 'Submit gems' || f.k === 'Recall') { end = f.r; break; }
      }
      const stunned = d.stun.some((s) => s[3] === b && s[1] >= e.r && s[1] <= end && s[2] >= 0);
      const hit = d.dmg.some((x) => x[3] === b && x[2] >= 0 && x[2] !== b && teamOf(x[2]) !== t && x[1] >= e.r && x[1] <= end);
      const lk = locks.some((l) => teamOf(l.who) !== t && l.r >= e.r && l.r <= end && l.to && cheb(l.to, [me[0], me[1]]) <= 3);
      if (outc === 'cancel' && stunned) outc = 'stunned';
      if (outc === 'cancel' && lk) outc = 'locked';
      let mn = 99;
      for (let r = e.r; r <= end; r++) mn = Math.min(mn, nearestOpp(r, b));
      const nk = mn <= 4 ? 'n<=4' : mn <= 8 ? 'n5-8' : 'n>8';
      inc(`trib|${t}|${bk}|n`); inc(`trib|${t}|${bk}|${outc}`); inc(`trib|${t}|${bk}|${nk}`); inc(`trib|${t}|${bk}|gems`, bag); inc(`trib|${t}|${bk}|turns`, end - e.r + 1);
      if (mn <= 8) { inc(`trib|${t}|${bk}|near8`); if (hit) inc(`trib|${t}|${bk}|near8hit`); if (stunned) inc(`trib|${t}|${bk}|near8stun`); if (lk) inc(`trib|${t}|${bk}|near8lock`); if (outc !== 'done') inc(`trib|${t}|${bk}|near8fail`); }
    } else if (e.k === 'Recall') {
      if (e.r - lastRec <= 5) { lastRec = e.r; continue; }
      lastRec = e.r;
      const me = P(e.r - 1, b); if (!me || !me[4] || onSpawn(t, me)) continue;
      const n = nearestOpp(e.r - 1, b);
      const nk = n <= 3 ? 'n<=3' : n <= 5 ? 'n4-5' : n <= 8 ? 'n6-8' : 'n>8';
      let res = 'interrupted';
      for (let r = e.r; r <= e.r + 7 && r <= FR; r++) { const c = P(r, b); if (!c) continue; if (!c[4]) { res = 'dead'; break; } if (onSpawn(t, c)) { res = 'done'; break; } }
      const hit = d.dmg.some((x) => x[3] === b && x[2] >= 0 && x[2] !== b && teamOf(x[2]) !== t && x[1] >= e.r && x[1] <= e.r + 5);
      const hpf = me[2] / me[3];
      inc(`rec|${t}|${nk}|n`); inc(`rec|${t}|${nk}|${res}`); if (hit) inc(`rec|${t}|${nk}|hit`); inc(`rec|${t}|${nk}|hpf`, hpf);
    }
  }
}
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), c: out }));
