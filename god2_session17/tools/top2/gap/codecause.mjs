#!/usr/bin/env node
// gap_g8_code: replay signatures of specific g8 code branches (bots/g8/src/brain.cpp), measured for both sides of each S0 game.
//   node tools/top2/gap/codecause.mjs SIDES.json DUMP.json.gz      (SIDES = C:/battlecode/cache/gap_g8/sides.json; "ours" = our team index)
// One JSON line per game: { file, c: { "<key>": n, ... } } with side = us | them in every key. Signatures:
//  A  arrival at a farmer (hit a camp in r-3..r-1, no enemy within 8 at r-1, one within 8 at r; enemy alive, not on its spawn),
//     split by the farmer's bag (0-9 / 10-21 / 22-53 / 54+) and round (<150 / >=150). Next 12 rounds: sub = started a tribute,
//     rec = started a recall, keep = camp damage in >= 2 of r..r+4 (and neither), alt = no tribute / recall but the distance to the
//     nearest altar fell by >= 3 within 6 rounds (altars = tiles tributed at in this game), other.
//     g8: tribute(false) runs right after combat() / safety(); `risky = enemy_near_field && gems >= tribute_risky (10)` makes a bag of
//     10+ walk to an altar as soon as an enemy is within 9 (brain.cpp tribute()).
//  C  capture -> recall: every CaptureGems: recall started by the capturer in r-6..r-1 (combo, lands with the reward), r..r+10 (after),
//     none; and the capture's Chebyshev distance from the own spawn (<= 8 / > 8). g8: capture_group() recalls when the group is > 8
//     walking steps from home and the body is rich (gold + reward gold >= cap_recall_gold 60), hurt (< 61%) or the bag reaches bank_min.
//  R  rally walk-in: a body of the side starts hitting a champion at round r (no champion damage by it in r-6..r-1). Every other body
//     of the side 3-9 tiles from it that was farming (camp damage in r-3..r-1, no champion damage) and is not channelling: next 5
//     rounds tow = 2+ tiles closer to the fight, keep = camp damage in >= 2 rounds, hit = dealt champion damage. Split by its health
//     share (< 0.6 / >= 0.6) and distance (3-5 / 6-9). g8: respond_to_alert() answers a RALLY within rally_r 9 at health >= rally_hp 0.6.
//  F  fight propensity vs the body's own earlier deaths: every 3rd round with an enemy within 4 (not on its spawn), own health >= 35%,
//     r < 1000: fight = champion damage in r..r+2. Split by local max-health ratio bucket (within 8), phase and prior deaths 0 / 1 / 2 /
//     3+. g8: Learner::fight_scale() = exp(fight_bias); every death within 8 rounds of a fight decision lowers fight_bias by 0.326 to a
//     floor of -0.6 (x0.55), never decaying (learn.cpp tick()).
//  T  tribute starts: bag (1-21 / 22-53 / 54-99 / 100+), round (<150 / >=150), enemy within 8 of the body in the 12 rounds before
//     (en / no), recall in the 25 rounds before (viaR / walk).
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const [sidesPath, file] = process.argv.slice(2);
const name = path.basename(file).replace(/\.json\.gz$/, '');
let d, sides;
try {
  sides = JSON.parse(fs.readFileSync(sidesPath, 'utf8'));
  d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
} catch (e) { console.log(JSON.stringify({ file: name, err: String(e) })); process.exit(0); }
const sd = sides[name];
if (!sd) { console.log(JSON.stringify({ file: name, err: 'no side' })); process.exit(0); }
const OURS = sd.ours;
const FR = d.meta.finalRound;
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const NB = Math.max(...d.meta.bodies.map((b) => b.index)) + 1;
const teamOf = (i) => B.get(i).team;
const sideOf = (t) => (t === OURS ? 'us' : 'them');
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
// ST[r][b] = [x, y, hp, maxHp, alive, gems, gold]
const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) {
  const row = d.R[i]; const r = row[0]; if (r < 1 || r > FR) continue;
  const a = new Array(NB); for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5], c[6], c[7]]; ST[r] = a;
}
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));
const spawn = [0, 1].map((t) => TB[t].map((b) => P(1, b)).filter(Boolean).map((p) => [p[0], p[1]]));
const onSpawn = (t, p) => spawn[t].some((s) => cheb(s, p) <= 1);
const spawnD = (t, p) => Math.min(...spawn[t].map((s) => cheb(s, p)));
const L = FR + 40;
const hc = Array.from({ length: NB }, () => new Uint8Array(L));
const hcamp = Array.from({ length: NB }, () => new Uint8Array(L));
const recall = Array.from({ length: NB }, () => new Uint8Array(L));
const submit = Array.from({ length: NB }, () => new Uint8Array(L));
for (const x of d.dmg) if (x[2] >= 0 && x[2] !== x[3] && B.has(x[2]) && B.has(x[3]) && teamOf(x[2]) !== teamOf(x[3])) hc[x[2]][x[1]] = 1;
for (const x of d.cdmg) if (B.has(x[2])) hcamp[x[2]][x[1]] = 1;
const altars = [];
const deaths = Array.from({ length: NB }, () => []);
for (const e of d.ev) {
  if (e.who === undefined || e.r > FR) continue;
  if (e.k === 'Recall') recall[e.who][e.r] = 1;
  if (e.k === 'Submit gems') {
    submit[e.who][e.r] = 1;
    if (e.to && !altars.some((a) => a[0] === e.to[0] && a[1] === e.to[1])) altars.push(e.to);
  }
  if (e.k === 'Death') deaths[e.who].push(e.r);
}
const any = (arr, a, b) => { for (let r = Math.max(0, a); r <= Math.min(L - 1, b); ++r) if (arr[r]) return true; return false; };
const cnt = (arr, a, b) => { let n = 0; for (let r = Math.max(0, a); r <= Math.min(L - 1, b); ++r) n += arr[r]; return n; };
const nearestEnemy = (r, b, pos) => {
  let m = 99;
  const t = teamOf(b);
  for (const e of TB[1 - t]) { const q = P(r, e); if (q && q[4] && !onSpawn(1 - t, q)) m = Math.min(m, cheb(pos, q)); }
  return m;
};
const altarD = (p) => { let m = 999; for (const a of altars) m = Math.min(m, cheb(p, a)); return m; };
const ratioB = (r, b) => {
  const me = P(r, b); let o = 0, t = 0;
  for (let i = 0; i < NB; ++i) {
    if (!B.has(i)) continue; const q = P(r, i); if (!q || !q[4] || cheb(q, me) > 8) continue;
    if (teamOf(i) === teamOf(b)) o += q[3]; else if (!onSpawn(teamOf(i), q)) t += q[3];
  }
  const x = t ? o / t : 9;
  return x < 0.67 ? 'a<.67' : x < 0.87 ? 'b.67-.87' : x < 1.15 ? 'c.87-1.15' : x < 1.5 ? 'd1.15-1.5' : 'e>1.5';
};
const c = {};
const inc = (k, n = 1) => { c[k] = (c[k] || 0) + n; };
const bagA = (g) => (g < 10 ? '0-9' : g < 22 ? '10-21' : g < 54 ? '22-53' : '54+');
const bagT = (g) => (g < 22 ? '1-21' : g < 54 ? '22-53' : g < 100 ? '54-99' : '100+');

for (const t of [0, 1]) {
  const s = sideOf(t);
  for (const b of TB[t]) {
    const priorDeaths = (r) => deaths[b].filter((x) => x < r).length;
    for (let r = 2; r <= FR - 12; ++r) {
      if (!alive(r, b) || !alive(r - 1, b)) continue;
      const p = P(r, b), p0 = P(r - 1, b);
      const pos = [p[0], p[1]];
      // A: arrival at a farmer
      if (any(hcamp[b], r - 3, r - 1) && nearestEnemy(r - 1, b, [p0[0], p0[1]]) > 8 && nearestEnemy(r, b, pos) <= 8) {
        const k = `A|${s}|${r < 150 ? 'e' : 'l'}|${bagA(p[5])}`;
        let resp;
        if (any(submit[b], r, r + 12)) resp = 'sub';
        else if (any(recall[b], r, r + 12)) resp = 'rec';
        else if (cnt(hcamp[b], r, r + 4) >= 2) resp = 'keep';
        else {
          let fell = false;
          if (altars.length) { const a0 = altarD(pos); for (let k2 = 1; k2 <= 6; ++k2) { const q = P(r + k2, b); if (q && q[4] && altarD([q[0], q[1]]) <= a0 - 3) { fell = true; break; } } }
          resp = fell ? 'alt' : 'other';
        }
        inc(`${k}|${resp}`);
        inc(`${k}|n`);
      }
      // F: fight propensity by prior deaths
      if (r < 1000 && r % 3 === 0 && p[2] >= 0.35 * p[3] && nearestEnemy(r, b, pos) <= 4) {
        const pd = Math.min(3, priorDeaths(r));
        const ph = r < 300 ? 'p0' : r < 600 ? 'p1' : 'p2';
        const f = any(hc[b], r, r + 2) ? 1 : 0;
        const k = `F|${s}|${ratioB(r, b)}|${ph}|d${pd}`;
        inc(`${k}|n`); inc(`${k}|fight`, f);
      }
      // R: rally walk-in (b is the fighter)
      if (hc[b][r] && !any(hc[b], r - 6, r - 1)) {
        for (const y of TB[t]) {
          if (y === b || !alive(r, y) || !alive(r + 5, y)) continue;
          const q = P(r, y); const dd = cheb([q[0], q[1]], pos);
          if (dd < 3 || dd > 9) continue;
          if (!any(hcamp[y], r - 3, r - 1) || any(hc[y], r - 3, r - 1) || any(recall[y], r - 5, r) || any(submit[y], r - 30, r)) continue;
          const hpB = q[2] >= 0.6 * q[3] ? 'hi' : 'lo';
          const dB = dd <= 5 ? 'd3-5' : 'd6-9';
          let best = dd; for (let k2 = 1; k2 <= 5; ++k2) { const z = P(r + k2, y); if (z && z[4]) best = Math.min(best, cheb([z[0], z[1]], pos)); }
          const tow = best <= dd - 2 ? 1 : 0;
          const keep = cnt(hcamp[y], r, r + 4) >= 2 ? 1 : 0;
          const hit = any(hc[y], r, r + 4) ? 1 : 0;
          const k = `R|${s}|${hpB}|${dB}`;
          inc(`${k}|n`); inc(`${k}|tow`, tow); inc(`${k}|keep`, keep); inc(`${k}|hit`, hit);
        }
      }
      // T: tribute starts
      if (submit[b][r]) {
        const bag = P(r, b)[5] || P(r - 1, b)[5];
        let en = false; for (let k2 = 1; k2 <= 12 && !en; ++k2) { const q = P(r - k2, b); if (q && q[4] && nearestEnemy(r - k2, b, [q[0], q[1]]) <= 8) en = true; }
        const via = any(recall[b], r - 25, r - 1) ? 'viaR' : 'walk';
        inc(`T|${s}|${r < 150 ? 'e' : 'l'}|${bagT(bag)}|${en ? 'en' : 'no'}|${via}`);
      }
    }
    // C: capture -> recall
    for (const e of d.ev) {
      if (e.k !== 'CaptureGems' || e.who !== b || e.r > FR) continue;
      const q = P(e.r, b); if (!q) continue;
      const far = spawnD(t, [q[0], q[1]]) > 8 ? 'far' : 'near';
      const combo = any(recall[b], e.r - 6, e.r - 1) ? 'combo' : any(recall[b], e.r, e.r + 10) ? 'after' : 'none';
      inc(`C|${s}|${far}|${combo}`);
    }
  }
}
console.log(JSON.stringify({ file: name, opp: sd.opp, c }));
