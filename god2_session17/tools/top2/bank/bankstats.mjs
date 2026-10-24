#!/usr/bin/env node
// god2 bank module (session 17): banking, channel and bag measurements per team from a tools/live/fightdump.mjs dump.
//   tributes: starts ('Submit gems'; a submit against an enemy lock is an 'Attack' event and is not counted), bag at the start (the
//     body's bag at the end of the previous round), outcome (done = 'Gems submitted' before the body acts again, dead, stunned, locked =
//     an opposing 'Place altar lock' within 3 during it, else cancel), starts of more than 2 turns (bag > 20) with an enemy within 7;
//   banks ('Banked'), banked gems at r300 / r600 / the end, bags lost at death (and deaths with 100+), the biggest bag, body-rounds
//     carrying 100+;
//   recalls started away from the own spawn (repeats within 5 rounds skipped): nearest enemy at the start <= 5, done (on spawn within 7
//     rounds), dead, interrupted;
//   heavy hits by a big bag: camp damage on monoliths / golems by a body carrying 100+;
//   enemy locks placed.
// One JSON line per game: {file, final, outcome, T: {0: {...}, 1: {...}}}.   node tools/top2/bank/bankstats.mjs DUMP.json.gz
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
// ST[r][body] = [x, y, hp, maxHp, alive, gems] at the end of round r
const ST = new Array(FR + 2);
const SUB = new Array(FR + 2);
for (let i = 0; i < d.R.length; ++i) {
  const row = d.R[i]; const r = row[0]; if (r < 0 || r > FR) continue;
  const a = new Array(NB); for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5], c[6]]; ST[r] = a; SUB[r] = [row[1], row[2]];
}
for (let r = 1; r <= FR; ++r) { if (!ST[r]) ST[r] = ST[r - 1]; if (!SUB[r]) SUB[r] = SUB[r - 1]; }
if (!ST[0]) ST[0] = ST[1];
if (!SUB[0]) SUB[0] = [0, 0];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))]?.[b];
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));
const spawn = [0, 1].map((t) => TB[t].map((b) => P(1, b)).filter(Boolean).map((p) => [p[0], p[1]]));
const onSpawn = (t, p) => spawn[t].some((s) => cheb(s, p) <= 2);
const nearestOpp = (r, b) => { const me = P(r, b); if (!me) return 99; let m = 99; for (const e of TB[1 - teamOf(b)]) { const q = P(r, e); if (q && q[4]) m = Math.min(m, cheb(q, me)); } return m; };
const heavy = new Set((d.meta.camps || []).filter((c) => c.type === 'monolith' || c.type === 5 || c.type === 'golem').map((c) => c.index));
const z = () => ({ tribStarts: 0, tribBag: 0, trib20: 0, trib20near7: 0, done: 0, dead: 0, stunned: 0, locked: 0, cancel: 0, doneBag: 0,
  banks: 0, banked: 0, sub300: 0, sub600: 0, subEnd: 0, deaths: 0, lostBag: 0, lost100: 0, maxBag: 0, bag100Rounds: 0,
  recalls: 0, recNear5: 0, recDone: 0, recDead: 0, recInt: 0, heavyHitsBig: 0, enemyLocks: 0, captures: 0, capGems: 0 });
const T = { 0: z(), 1: z() };
const evBy = new Map();
for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
const locks = d.ev.filter((e) => e.k === 'Place altar lock');
for (const l of locks) if (l.who !== undefined) T[1 - teamOf(l.who)].enemyLocks++;
for (const [b, evs] of evBy) {
  const t = teamOf(b); const S = T[t];
  let lastRec = -99;
  for (let i = 0; i < evs.length; i++) {
    const e = evs[i];
    if (e.k === 'Banked') { S.banks++; S.banked += e.gems; }
    else if (e.k === 'CaptureGems') { S.captures++; S.capGems += e.gems; }
    else if (e.k === 'Death') { S.deaths++; S.lostBag += e.bag || 0; if ((e.bag || 0) >= 100) S.lost100++; }
    else if (e.k === 'Submit gems') {
      const me = P(e.r - 1, b); if (!me || !me[4]) continue;
      const bag = me[5];
      S.tribStarts++; S.tribBag += bag;
      if (bag > 20) { S.trib20++; if (nearestOpp(e.r - 1, b) <= 7) S.trib20near7++; }
      let end = Math.min(FR, e.r + Math.ceil(bag / 10) + 3), outc = 'cancel';
      for (let j = i + 1; j < evs.length; j++) {
        const f = evs[j];
        if (f.k === 'Gems submitted') { end = f.r; outc = 'done'; break; }
        if (f.k === 'Death') { end = f.r; outc = 'dead'; break; }
        if (f.k === 'Move' || f.k === 'Attack' || f.k === 'Cast ability' || f.k === 'Submit gems' || f.k === 'Recall') { end = f.r; break; }
      }
      const stunned = d.stun.some((s) => s[3] === b && s[1] >= e.r && s[1] <= end && s[2] >= 0);
      const lk = locks.some((l) => teamOf(l.who) !== t && l.r >= e.r && l.r <= end && l.to && cheb(l.to, [me[0], me[1]]) <= 3);
      if (outc === 'cancel' && stunned) outc = 'stunned';
      if (outc === 'cancel' && lk) outc = 'locked';
      S[outc]++;
      if (outc === 'done') S.doneBag += bag;
    } else if (e.k === 'Recall') {
      if (e.r - lastRec <= 5) { lastRec = e.r; continue; }
      lastRec = e.r;
      const me = P(e.r - 1, b); if (!me || !me[4] || onSpawn(t, me)) continue;
      S.recalls++;
      if (nearestOpp(e.r - 1, b) <= 5) S.recNear5++;
      let res = 'recInt';
      for (let r = e.r; r <= e.r + 7 && r <= FR; r++) { const c = P(r, b); if (!c) continue; if (!c[4]) { res = 'recDead'; break; } if (onSpawn(t, c)) { res = 'recDone'; break; } }
      S[res]++;
    }
  }
}
for (const x of d.cdmg) {
  const [, r, a, camp] = x;
  if (!heavy.has(camp)) continue;
  const me = P(r - 1, a); if (!me || me[5] < 100) continue;
  T[teamOf(a)].heavyHitsBig++;
}
for (let r = 1; r <= FR; ++r) {
  const s = ST[r]; if (!s) continue;
  for (let b = 0; b < NB; ++b) { const c = s[b]; if (!c || !c[4] || !B.has(b)) continue; const S = T[teamOf(b)]; if (c[5] > S.maxBag) S.maxBag = c[5]; if (c[5] >= 100) S.bag100Rounds++; }
}
for (const t of [0, 1]) {
  T[t].sub300 = SUB[Math.min(300, FR)][t]; T[t].sub600 = SUB[Math.min(600, FR)][t]; T[t].subEnd = (d.meta.submitted || SUB[FR])[t];
}
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, '.repl26a'), final: FR, outcome: d.meta.outcome, T }));
