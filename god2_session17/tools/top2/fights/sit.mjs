#!/usr/bin/env node
// Situation -> action -> outcome miner for the top-team fights study (experiments/top2/an_fights.md), over tools/live/fightdump.mjs dumps.
// One JSON line per game; every record carries the team index t (0 / 1): the aggregator (agg.py) splits study team vs opponent.
//   node tools/top2/fights/sit.mjs SIDES.json GEO.json C:/battlecode/cache/t2dump/<key>/<map>_<id8>.json.gz
// Records (see the field lists below): smp decision samples (every 3rd round with an enemy within 8), arr enemy arrives while
// farming, ast ally hit nearby (per ally), cap capture -> bank decision, bnk tribute channels, low low-health crossings, rcl
// recall attempts, omt fresh outmatched / outmatching states, pun enemy channels near us, lck altar locks, eng engagements with
// aftermath, chs chases, dth deaths with context, ctc fresh contacts (who strikes first).
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const [sidesFile, geoFile, file] = process.argv.slice(2);
const name = path.basename(file).replace(/\.json\.gz$/, '');
const key = path.basename(path.dirname(file));
const SIDES = JSON.parse(fs.readFileSync(sidesFile, 'utf8'));
const SD = (SIDES[key] || {})[name];
const out0 = { file: path.basename(file), key, game: name };
if (!SD) { console.log(JSON.stringify({ ...out0, err: 'no side' })); process.exit(0); }
const GEO = JSON.parse(fs.readFileSync(geoFile, 'utf8'));
const G = GEO[SD.map];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ ...out0, err: String(e) })); process.exit(0); }

// ------------------------------------------------------------------------------------------------ state arrays
const FR = d.meta.finalRound;
const W = d.meta.width, H = d.meta.height;
const NB = Math.max(...d.meta.bodies.map((b) => b.index)) + 1;
const TEAM = new Int8Array(NB).fill(-1), TYPE = new Array(NB).fill('?');
for (const b of d.meta.bodies) { TEAM[b.index] = b.team; TYPE[b.index] = b.type; }
const TB = [[], []];
for (const b of d.meta.bodies) TB[b.team].push(b.index);
const ALLB = d.meta.bodies.map((b) => b.index);
const mkA = (T, n = FR + 3) => Array.from({ length: NB }, () => new T(n));
const X = mkA(Int16Array), Y = mkA(Int16Array), HP = mkA(Float32Array), MH = mkA(Float32Array), AL = mkA(Uint8Array), GM = mkA(Int32Array);
const GD = mkA(Int32Array), KL = mkA(Int16Array), SN = mkA(Uint8Array);
const filled = new Uint8Array(FR + 3);
for (let i = 1; i < d.R.length; ++i) {
  const row = d.R[i], r = row[0];
  if (r < 1 || r > FR) continue;
  filled[r] = 1;
  for (const c of row[3]) { const b = c[0]; X[b][r] = c[1]; Y[b][r] = c[2]; HP[b][r] = c[3]; MH[b][r] = c[4]; AL[b][r] = c[5]; GM[b][r] = c[6]; GD[b][r] = c[7]; KL[b][r] = c[8]; SN[b][r] = c[9]; }
}
const copyR = (dst, src) => { for (const b of ALLB) { X[b][dst] = X[b][src]; Y[b][dst] = Y[b][src]; HP[b][dst] = HP[b][src]; MH[b][dst] = MH[b][src]; AL[b][dst] = AL[b][src]; GM[b][dst] = GM[b][src]; GD[b][dst] = GD[b][src]; KL[b][dst] = KL[b][src]; SN[b][dst] = SN[b][src]; } };
for (let r = 2; r <= FR; ++r) if (!filled[r]) copyR(r, r - 1);
copyR(0, 1); copyR(FR + 1, FR); copyR(FR + 2, FR);
const cl = (r) => Math.max(0, Math.min(FR + 2, r));
const alive = (b, r) => AL[b][cl(r)] === 1;
const dist = (a, ra, b, rb) => Math.max(Math.abs(X[a][cl(ra)] - X[b][cl(rb)]), Math.abs(Y[a][cl(ra)] - Y[b][cl(rb)]));
const dpt = (b, r, x, y) => Math.max(Math.abs(X[b][cl(r)] - x), Math.abs(Y[b][cl(r)] - y));
const hpf = (b, r) => MH[b][cl(r)] > 0 ? HP[b][cl(r)] / MH[b][cl(r)] : 0;
const moved = (b, r) => alive(b, r) && alive(b, r - 1) && (X[b][r] !== X[b][r - 1] || Y[b][r] !== Y[b][r - 1]);

// ------------------------------------------------------------------------------------------------ map geometry
const spawnSets = [new Set(), new Set()];
let swap = false;
{
  const near = (list, x, y) => list.some(([a, c]) => Math.max(Math.abs(a - x), Math.abs(c - y)) <= 3);
  const nA = TB[0].filter((b) => near(G.spawnA, X[b][1], Y[b][1])).length, nB = TB[0].filter((b) => near(G.spawnB, X[b][1], Y[b][1])).length;
  swap = nB > nA;
  for (const [x, y] of G.spawnA) spawnSets[swap ? 1 : 0].add(x * 1000 + y);
  for (const [x, y] of G.spawnB) spawnSets[swap ? 0 : 1].add(x * 1000 + y);
}
const HD = swap ? [G.dB, G.dA] : [G.dA, G.dB]; // walking distance from each team's spawn, flat y * W + x, -1 unreachable
const onSpawn = (b, r) => spawnSets[TEAM[b]].has(X[b][cl(r)] * 1000 + Y[b][cl(r)]);
const spawnList = [0, 1].map((t) => [...spawnSets[t]].map((k) => [Math.floor(k / 1000), k % 1000]));
const nearSpawnT = (t, x, y, R) => spawnList[t].some(([a, c]) => Math.max(Math.abs(a - x), Math.abs(c - y)) <= R);
const nearSpawn = (b, r, R = 2) => nearSpawnT(TEAM[b], X[b][cl(r)], Y[b][cl(r)], R);
const spawnC = [0, 1].map((t) => { const l = spawnList[t]; return [l.reduce((s, p) => s + p[0], 0) / l.length, l.reduce((s, p) => s + p[1], 0) / l.length]; });
const homeD = (t, x, y) => { const v = HD[t][y * W + x]; return v >= 0 ? v : 999; };
// zone of a tile for team t: share of walking distance own / (own + their)
const zfrac = (t, x, y) => { const a = homeD(t, x, y), b = homeD(1 - t, x, y); return a + b > 0 && a < 999 && b < 999 ? a / (a + b) : 0.5; };
const zoneOf = (t, x, y) => { const f = zfrac(t, x, y); return f < 0.4 ? 0 : f > 0.6 ? 2 : 1; };
// grid orientation check (altars must be 'A')
const gridAt = (() => {
  const g = G.grid;
  const ok = G.altars.every(([x, y]) => g[y] && g[y][x] === 'A');
  return ok ? (x, y) => g[y][x] : (x, y) => g[x][y];
})();
const walkable = (x, y) => x >= 0 && y >= 0 && x < W && y < H && '#oA'.indexOf(gridAt(x, y)) < 0;
// walking distance to the nearest tile from which a tribute can start (Chebyshev 1 of an altar)
const AD = new Int16Array(W * H).fill(-1);
{
  const qx = [], qy = [];
  for (const [ax, ay] of G.altars) for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) {
    const x = ax + dx, y = ay + dy;
    if (walkable(x, y) && AD[y * W + x] < 0) { AD[y * W + x] = 0; qx.push(x); qy.push(y); }
  }
  for (let h = 0; h < qx.length; ++h) {
    const x = qx[h], y = qy[h], v = AD[y * W + x];
    for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) {
      const nx = x + dx, ny = y + dy;
      if ((dx || dy) && walkable(nx, ny) && AD[ny * W + nx] < 0) { AD[ny * W + nx] = v + 1; qx.push(nx); qy.push(ny); }
    }
  }
}
const altarD = (b, r) => { const v = AD[Y[b][cl(r)] * W + X[b][cl(r)]]; return v >= 0 ? v : 999; };

// camp groups (cardinally connected camps)
const CAMPS = d.meta.camps;
const cIdx = new Map(CAMPS.map((c, i) => [c.index, i]));
const par = CAMPS.map((_, i) => i);
const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
{
  const at = new Map(CAMPS.map((c, i) => [c.x * 1000 + c.y, i]));
  CAMPS.forEach((c, i) => { for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(i)] = find(j); } });
}
const GEMV = { wolf: 4, elk: 15, gem: 7, gold: 0, monolith: 200, golem: 36, 5: 36 }, GOLDV = { wolf: 40, elk: 90, gem: 0, gold: 20, monolith: 300, golem: 160, 5: 160 };
const groupOfCamp = new Int16Array(CAMPS.length);
const groups = [];
{
  const gid = new Map();
  CAMPS.forEach((c, i) => {
    const root = find(i);
    if (!gid.has(root)) { gid.set(root, groups.length); groups.push({ tiles: [], gems: 0, gold: 0, hp: 0, types: {} }); }
    const g = groups[gid.get(root)];
    groupOfCamp[i] = gid.get(root);
    g.tiles.push([c.x, c.y]); g.gems += GEMV[c.type] || 0; g.gold += GOLDV[c.type] || 0; g.hp += c.hp; g.types[c.type] = (g.types[c.type] || 0) + 1;
  });
  for (const g of groups) { g.cx = g.tiles.reduce((s, p) => s + p[0], 0) / g.tiles.length; g.cy = g.tiles.reduce((s, p) => s + p[1], 0) / g.tiles.length; }
}
const tileGroup = new Map();
groups.forEach((g, i) => g.tiles.forEach(([x, y]) => tileGroup.set(x * 1000 + y, i)));
const groupNear = (x, y) => { // group whose tile is within 1 of (x, y)
  for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) { const g = tileGroup.get((x + dx) * 1000 + y + dy); if (g !== undefined) return g; }
  return -1;
};
const distGroup = (b, r, g) => { let m = 99; for (const [x, y] of groups[g].tiles) m = Math.min(m, dpt(b, r, x, y)); return m; };

// ------------------------------------------------------------------------------------------------ events
const F32 = () => mkA(Float32Array), U8 = () => mkA(Uint8Array);
const hc = F32(), tc = F32(), tcamp = F32(), hcamp = F32(), healIn = F32();
const rec = U8(), can = U8(), sub = U8(), mvE = U8(), atkE = U8(), castE = U8(), actE = U8(), stunIn = U8(), shopE = U8();
const campHitG = mkA(Int16Array); for (const a of campHitG) a.fill(-1);
const deathsRaw = d.ev.filter((e) => e.k === 'Death');
const evAt = new Map(); // q -> action event (Attack / Cast)
for (const e of d.ev) {
  if (e.who === undefined || e.who < 0 || e.who >= NB) continue;
  const b = e.who, r = Math.min(e.r, FR + 2);
  switch (e.k) {
    case 'Move': mvE[b][r]++; actE[b][r] = 1; break;
    case 'Attack': atkE[b][r]++; actE[b][r] = 1; evAt.set(e.q, e); break;
    case 'Cast ability': castE[b][r]++; actE[b][r] = 1; evAt.set(e.q, e); break;
    case 'Recall': rec[b][r] = 1; break;
    case 'Cancel channel': can[b][r] = 1; break;
    case 'Submit gems': sub[b][r] = 1; actE[b][r] = 1; break;
    case 'Shop': shopE[b][r] = 1; break;
    case 'Place ward': case 'Consumable': case 'Place altar lock': actE[b][r] = 1; break;
    default: break;
  }
}
// Cassi & Issac double deaths: keep the body that was actually hit, mark the partner as linked (and its damage record as phantom)
const linked = new Set(), phantom = new Set();
{
  const byQ = new Map();
  for (const e of deathsRaw) { if (!byQ.has(e.q)) byQ.set(e.q, []); byQ.get(e.q).push(e); }
  for (const [q, es] of byQ) {
    const ci = es.filter((e) => TYPE[e.who] === 'Cassi' || TYPE[e.who] === 'Issac');
    if (ci.length === 2 && TEAM[ci[0].who] === TEAM[ci[1].who]) {
      const a = evAt.get(q);
      let real = ci[0], other = ci[1];
      if (a && a.to) {
        const d0 = Math.max(Math.abs(ci[0].at[0] - a.to[0]), Math.abs(ci[0].at[1] - a.to[1]));
        const d1 = Math.max(Math.abs(ci[1].at[0] - a.to[0]), Math.abs(ci[1].at[1] - a.to[1]));
        if (d1 < d0) { real = ci[1]; other = ci[0]; }
      }
      linked.add(other.q * 64 + other.who); phantom.add(q * 64 + other.who);
    } else if (ci.length === 1) {
      // a partner dying alone in a step where the other C&I body died earlier is not possible; nothing to do
    }
  }
}
const cc = []; // champion damage on enemy champions: [q, r, a, v, amt, kind, slot]
for (const x of d.dmg) {
  const [q, r, a, v, amt] = x;
  if (v < 0 || v >= NB || r > FR + 2) continue;
  if (phantom.has(q * 64 + v)) continue;
  if (a < 0) { tcamp[v][r] += amt; continue; }
  if (a === v) { tc[v][r] += amt; continue; } // Ren reflect on the actor
  if (TEAM[a] === TEAM[v]) continue;
  hc[a][r] += amt; tc[v][r] += amt; cc.push(x);
}
cc.sort((a, b) => a[0] - b[0]);
for (const x of d.cdmg) { const [q, r, a, ci, amt] = x; if (a < 0 || a >= NB || r > FR + 2) continue; hcamp[a][r] += amt; const i = cIdx.get(ci); if (i !== undefined) campHitG[a][r] = groupOfCamp[i]; }
for (const x of d.heal) { const [q, r, a, v, amt] = x; if (v >= 0 && v < NB && r <= FR + 2) healIn[v][r] += amt; }
const stunBy = [];
for (const x of d.stun) { const [q, r, a, v] = x; if (v >= 0 && v < NB && r <= FR + 2) { stunIn[v][r] = 1; stunBy.push(x); } }
const deaths = deathsRaw.filter((e) => !linked.has(e.q * 64 + e.who)).map((e) => ({ ...e, r: Math.min(e.r, FR) }));
const diedAt = Array.from({ length: NB }, () => []);
for (const e of deathsRaw) diedAt[e.who].push(e.r);
const diesWithin = (b, r0, r1) => diedAt[b].some((x) => x >= r0 && x <= r1);
const kills = deaths.filter((e) => typeof e.by === 'number');
// captures per body-round: gems or gold up without a kill (Marcella's tribute gold excluded by the bank check below)
const banksEv = d.ev.filter((e) => e.k === 'Gems submitted' && e.who !== undefined);
const bankR = U8();
for (const e of banksEv) bankR[e.who][Math.min(e.r, FR + 2)] = 1;
const capR = mkA(Int16Array); // gems captured this round (or -1 for a gold-only capture)
const caps = []; // {b, t, r, gems, gold, g}
for (const b of ALLB) for (let r = 2; r <= FR; ++r) {
  if (!alive(b, r) || !alive(b, r - 1)) continue;
  const dg = GM[b][r] - GM[b][r - 1], dgo = GD[b][r] - GD[b][r - 1], dk = KL[b][r] - KL[b][r - 1];
  if (dk > 0 || bankR[b][r]) continue;
  if (dg > 0 || (dgo >= 10 && !shopE[b][r])) {
    const g = groupNear(X[b][r - 1], Y[b][r - 1]); // captures resolve at round start: the body stood there at the end of r - 1
    if (g < 0 && dg <= 0) continue;
    capR[b][r] = dg > 0 ? dg : -1;
    caps.push({ b, t: TEAM[b], r, gems: Math.max(0, dg), gold: Math.max(0, dgo), g });
  }
}

// ------------------------------------------------------------------------------------------------ channels: recalls and tributes
const spam = [0, 1].map((t) => TB[t].reduce((s, b) => s + can[b].reduce((a, v) => a + v, 0), 0) > 40 ? 1 : 0);
const teleR = U8(); // recall arrival rounds
for (const b of ALLB) for (let r = 2; r <= FR; ++r) {
  if (alive(b, r) && alive(b, r - 1) && nearSpawn(b, r, 2) && !nearSpawn(b, r - 1, 3) && dist(b, r, b, r - 1) >= 4) teleR[b][r] = 1;
}
const recalls = []; // recall attempts (every Recall off spawn for normal teams; committed ones for recall-spam teams)
{
  const dmgOn = Array.from({ length: NB }, () => []); // [q, r] any damage on b (champion or camp), plus stuns
  for (const x of d.dmg) { if (x[3] >= 0 && x[3] < NB && !phantom.has(x[0] * 64 + x[3])) dmgOn[x[3]].push([x[0], x[1]]); }
  for (const x of d.stun) if (x[3] >= 0 && x[3] < NB) dmgOn[x[3]].push([x[0], x[1]]);
  for (const a of dmgOn) a.sort((u, v) => u[0] - v[0]);
  const recEvs = d.ev.filter((e) => e.k === 'Recall' && e.who !== undefined && e.who >= 0 && e.who < NB);
  const lastRecBefore = (b, k) => { let m = -1; for (const e of recEvs) { if (e.who !== b) continue; if (e.r < k) m = Math.max(m, e.q); } return m; };
  for (const e of recEvs) {
    const b = e.who, r = Math.min(e.r, FR);
    if (!alive(b, r) || nearSpawn(b, r - 1, 2)) continue;
    let done = 0;
    for (let k = r + 1; k <= Math.min(FR, r + 6); ++k) if (teleR[b][k]) { done = k; break; }
    if (done && lastRecBefore(b, done) !== e.q) continue; // an earlier, cancelled channel
    const committed = done || (alive(b, r + 1) && !can[b][r + 1] && !actE[b][r + 1] && !stunIn[b][r + 1] && !SN[b][r + 1]) ? 1 : 0;
    const attempt = spam[TEAM[b]] ? committed : 1;
    if (!attempt) continue;
    const endR = done || r + 5;
    let firstHit = -1;
    for (const [q, k] of dmgOn[b]) { if (q <= e.q) continue; if (k > endR) break; firstHit = k; break; }
    let res = 'cancel';
    if (done) res = 'done';
    else if (diesWithin(b, r, r + 6)) res = 'killed';
    else if (firstHit >= 0) res = 'interrupted';
    recalls.push({ b, t: TEAM[b], r, q: e.q, committed, res, done, firstHit, hpf: hpf(b, r - 1), bag: GM[b][r - 1] });
  }
}
const tributes = []; // tribute channels
{
  const subs = d.ev.filter((e) => e.k === 'Submit gems' && e.who !== undefined);
  const locksEv = d.ev.filter((e) => e.k === 'Place altar lock' && e.who !== undefined);
  for (const e of subs) {
    const b = e.who, r = Math.min(e.r, FR), bag0 = Math.max(GM[b][r - 1], GM[b][r]);
    const dur = Math.max(1, Math.ceil(bag0 / 10));
    const nxtSub = subs.find((s) => s.who === b && s.q > e.q);
    const done = banksEv.find((s) => s.who === b && s.q > e.q && (!nxtSub || s.q < nxtSub.q) && s.r <= r + dur + 3);
    let res = done ? 'done' : 'cancel';
    const endR = done ? done.r : r + dur + 1;
    if (!done) {
      if (diesWithin(b, r, endR)) res = 'killed';
      else if (stunBy.some((s) => s[3] === b && s[1] >= r && s[1] <= endR && s[2] >= 0 && TEAM[s[2]] !== TEAM[b])) res = 'stunned';
      else if (locksEv.some((l) => TEAM[l.who] !== TEAM[b] && l.r >= r && l.r <= endR && l.to && Math.max(Math.abs(l.to[0] - e.to[0]), Math.abs(l.to[1] - e.to[1])) === 0)) res = 'locked';
    }
    tributes.push({ b, t: TEAM[b], r, q: e.q, bag: bag0, dur, res, endR, altar: e.to });
  }
}
// channel state per body-round (for "busy" flags): 1 recall channel (committed), 2 tribute
const chan = U8();
for (const c of recalls) if (c.committed) for (let k = c.r; k <= Math.min(FR, c.done || c.r + 5); ++k) { if (k > c.r && (actE[c.b][k] || can[c.b][k])) break; chan[c.b][k] = 1; }
for (const c of tributes) for (let k = c.r; k <= Math.min(FR, c.endR); ++k) chan[c.b][k] = 2;

// ------------------------------------------------------------------------------------------------ local state helpers
const enemyOK = (e, r) => alive(e, r) && !onSpawn(e, r);
const nearestEnemy = (b, r) => { let m = 99, w = -1; for (const e of TB[1 - TEAM[b]]) if (enemyOK(e, r)) { const v = dist(b, r, e, r); if (v < m) { m = v; w = e; } } return [m, w]; };
const localState = (b, r, R) => { // allies incl. b and enemies within R of b at the end of round r
  const o = { nA: 0, nE: 0, hpA: 0, hpE: 0, mhA: 0, mhE: 0 };
  for (const u of ALLB) {
    if (!alive(u, r) || dist(b, r, u, r) > R) continue;
    if (TEAM[u] === TEAM[b]) { o.nA++; o.hpA += HP[u][r]; o.mhA += MH[u][r]; } else if (!onSpawn(u, r)) { o.nE++; o.hpE += HP[u][r]; o.mhE += MH[u][r]; }
  }
  return o;
};
const busyOf = (b, r) => { // 1 farming (hit a camp in r-1..r), 2 standing on a camp tile, 3 recall channel, 4 tribute channel
  if (chan[b][r] === 2) return 4;
  if (chan[b][r] === 1) return 3;
  if (hcamp[b][r] > 0 || hcamp[b][r - 1] > 0) return 1;
  if (!moved(b, r) && groupNear(X[b][r], Y[b][r]) >= 0 && tileGroup.has(X[b][r] * 1000 + Y[b][r])) return 2;
  return 0;
};
// action over rounds r+1..r+W relative to the enemy e (or the nearest enemy each round)
const ACT = { fight: 0, farm: 1, away: 2, toward: 3, hold: 4, recall: 5, bank: 6, dead: 7 };
const windowAct = (b, r, Wn, e) => {
  let f = 0, c = 0, rc = 0, bk = 0, dead = 0, firstF = -1;
  for (let k = r + 1; k <= Math.min(FR, r + Wn); ++k) {
    if (!alive(b, k)) { dead = 1; break; }
    if (hc[b][k] > 0) { f++; if (firstF < 0) firstF = k - r; }
    if (hcamp[b][k] > 0 || capR[b][k]) c++;
    if (chan[b][k] === 1 && chan[b][k - 1] !== 1) rc++;
    if (sub[b][k]) bk++;
  }
  const kE = Math.min(FR, r + Wn);
  let dn = 0, hm = 0;
  if (alive(b, kE) && e >= 0) dn = dist(b, kE, e, kE) - dist(b, r, e, r);
  if (alive(b, kE)) hm = homeD(TEAM[b], X[b][kE], Y[b][kE]) - homeD(TEAM[b], X[b][r], Y[b][r]);
  let a;
  if (f) a = ACT.fight;
  else if (rc || chan[b][Math.min(FR, r + 1)] === 1) a = ACT.recall;
  else if (bk) a = ACT.bank;
  else if (dead) a = ACT.dead;
  else if (c) a = ACT.farm;
  else if (dn >= 2 || (hm <= -2 && dn >= 0)) a = ACT.away;
  else if (dn <= -2) a = ACT.toward;
  else a = ACT.hold;
  return { a, f, c, dn, hm, firstF, dead };
};
const sumOver = (arr, b, r0, r1) => { let s = 0; for (let k = Math.max(0, r0); k <= Math.min(FR, r1); ++k) s += arr[b][k]; return s; };
const enemyDeathsNear = (t, x, y, r0, r1, R) => deaths.filter((e) => e.team !== t && e.r >= r0 && e.r <= r1 && Math.max(Math.abs(e.at[0] - x), Math.abs(e.at[1] - y)) <= R).length;
const r2 = (v) => Math.round(v * 100) / 100;
const typeId = (b) => TYPE[b];

// ------------------------------------------------------------------------------------------------ smp: decision samples
// [t, type, r, busy, bag, hpf%, dNear, nA8, nE8, hpA8, hpE8, mhA8, mhE8, zone, act3, died10, ekill10, out5, in5, nA4, nE4, nearType, eBag8, nearHp%]
const smp = [];
for (let r = 3; r <= FR - 1; r += 3) for (const b of ALLB) {
  if (!alive(b, r) || onSpawn(b, r)) continue;
  const [dn, e] = nearestEnemy(b, r);
  if (dn > 8) continue;
  const L = localState(b, r, 8), L4 = localState(b, r, 4);
  const wa = windowAct(b, r, 3, e);
  smp.push([TEAM[b], typeId(b), r, busyOf(b, r), GM[b][r], Math.round(hpf(b, r) * 100), dn, L.nA, L.nE, Math.round(L.hpA), Math.round(L.hpE), Math.round(L.mhA), Math.round(L.mhE),
    zoneOf(TEAM[b], X[b][r], Y[b][r]), wa.a, diesWithin(b, r + 1, r + 10) ? 1 : 0, enemyDeathsNear(TEAM[b], X[b][r], Y[b][r], r + 1, r + 10, 8),
    Math.round(sumOver(hc, b, r + 1, r + 5)), Math.round(sumOver(tc, b, r + 1, r + 5) + sumOver(tcamp, b, r + 1, r + 5)), L4.nA, L4.nE, typeId(e),
    TB[1 - TEAM[b]].reduce((m, u) => (enemyOK(u, r) && dist(b, r, u, r) <= 8 ? Math.max(m, GM[u][r]) : m), 0), Math.round(hpf(e, r) * 100)]);
}

// ------------------------------------------------------------------------------------------------ arr: enemy arrives while farming
const arr = [];
for (const b of ALLB) {
  let lastArr = -99;
  for (let r = 6; r <= FR - 1; ++r) {
    if (!alive(b, r) || onSpawn(b, r)) continue;
    const farmNow = hcamp[b][r] > 0 || hcamp[b][r - 1] > 0 || hcamp[b][r - 2] > 0;
    const capNow = !farmNow && !moved(b, r) && !moved(b, r - 1) && tileGroup.has(X[b][r] * 1000 + Y[b][r]);
    if (!farmNow && !capNow) continue;
    const [dn, e] = nearestEnemy(b, r);
    if (dn > 8) continue;
    let fresh = true;
    for (let k = r - 4; k < r; ++k) if (nearestEnemy(b, k)[0] <= 8) { fresh = false; break; }
    if (!fresh || r - lastArr < 10) continue;
    lastArr = r;
    let g = -1; for (let k = r; k >= r - 2 && g < 0; --k) g = campHitG[b][k];
    if (g < 0) g = groupNear(X[b][r], Y[b][r]);
    const L = localState(b, r, 8);
    const wa = windowAct(b, r, 5, e);
    // group progress: damage dealt to this group by b's team in the last 30 rounds / group hp
    let gd = 0;
    if (g >= 0) for (const x of d.cdmg) { if (x[1] > r || x[1] < r - 30) continue; const i = cIdx.get(x[3]); if (i !== undefined && groupOfCamp[i] === g && x[2] >= 0 && TEAM[x[2]] === TEAM[b]) gd += x[4]; }
    // capture of this group within 40 rounds by b's team / the enemy
    let capT = -1, capBy = -1;
    if (g >= 0) for (const c of caps) if (c.g === g && c.r > r && c.r <= r + 40) { capT = c.r - r; capBy = c.t === TEAM[b] ? 0 : 1; break; }
    const eApproached = alive(e, r - 1) && dist(b, r, e, r - 1) > dist(b, r, e, r) ? 1 : 0;
    arr.push({ t: TEAM[b], ty: typeId(b), r, cap: capNow ? 1 : 0, bag: GM[b][r], hpf: r2(hpf(b, r)), dn, eTy: typeId(e), eAppr: eApproached, nA: L.nA, nE: L.nE, hpA: Math.round(L.hpA), hpE: Math.round(L.hpE),
      mhA: Math.round(L.mhA), mhE: Math.round(L.mhE), z: zoneOf(TEAM[b], X[b][r], Y[b][r]), g, gGems: g >= 0 ? groups[g].gems : 0, gHp: g >= 0 ? groups[g].hp : 0, prog: g >= 0 ? r2(Math.min(1, gd / Math.max(1, groups[g].hp))) : 0,
      a: wa.a, nF: wa.f, nC: wa.c, firstF: wa.firstF, eFirst: (() => { for (let k = r + 1; k <= r + 5; ++k) if (tc[b][k] > 0) return k - r; return -1; })(),
      died20: diesWithin(b, r + 1, r + 20) ? 1 : 0, ek20: enemyDeathsNear(TEAM[b], X[b][r], Y[b][r], r + 1, r + 20, 10), capT, capBy,
      out10: Math.round(sumOver(hc, b, r + 1, r + 10)), in10: Math.round(sumOver(tc, b, r + 1, r + 10)) });
  }
}

// ------------------------------------------------------------------------------------------------ ast: an ally is hit (first hit of a sequence)
const ast = [];
for (const x of cc) {
  const [q, r, a, v] = x;
  if (r < 2 || r > FR - 2) continue;
  let fresh = true;
  for (let k = r - 6; k < r; ++k) if (k >= 0 && tc[v][k] > 0) { fresh = false; break; }
  if (!fresh) continue;
  if (ast.some((s) => s.v === v && s.r === r)) continue;
  const vx = X[v][r - 1], vy = Y[v][r - 1];
  const vDied = diesWithin(v, r, r + 15) ? 1 : 0;
  const aDied = diesWithin(a, r, r + 15) ? 1 : 0;
  const Lv = localState(v, r - 1, 8);
  const helpers = [];
  for (const u of TB[TEAM[v]]) {
    if (u === v || !alive(u, r - 1) || onSpawn(u, r - 1)) continue;
    const d0 = dpt(u, r - 1, vx, vy);
    if (d0 > 20) continue;
    if ((TYPE[u] === 'Cassi' && TYPE[v] === 'Issac') || (TYPE[u] === 'Issac' && TYPE[v] === 'Cassi')) continue; // linked partner moves on its own logic but shares fate
    let hit = -1, hitAtk = 0, minD = d0, approach = -1;
    for (let k = r; k <= Math.min(FR, r + 10); ++k) {
      if (!alive(u, k)) break;
      if (hit < 0 && hc[u][k] > 0) {
        // the hit counts as help if its victim was within 8 of the ally under attack
        const hs = cc.filter((y) => y[1] === k && y[2] === u);
        if (hs.some((y) => dist(y[3], k, v, Math.min(k, alive(v, k) ? k : r)) <= 8 || y[3] === a)) { hit = k - r; hitAtk = hs.some((y) => y[3] === a) ? 1 : 0; }
      }
      const dd = alive(v, k) ? dist(u, k, v, k) : dpt(u, k, vx, vy);
      if (dd < minD) minD = dd;
      if (approach < 0 && dd <= 4) approach = k - r;
    }
    const k5 = Math.min(FR, r + 5);
    const d5 = alive(u, k5) ? (alive(v, k5) ? dist(u, k5, v, k5) : dpt(u, k5, vx, vy)) : null;
    helpers.push([typeId(u), d0, busyOf(u, r - 1), Math.round(hpf(u, r - 1) * 100), hit, hitAtk, approach, d5, minD, GM[u][r - 1]]);
  }
  ast.push({ t: TEAM[v], v, r, vTy: typeId(v), aTy: typeId(a), vHp: r2(hpf(v, r - 1)), vBusy: busyOf(v, r - 1), nA: Lv.nA, nE: Lv.nE, mhA: Math.round(Lv.mhA), mhE: Math.round(Lv.mhE),
    hpA: Math.round(Lv.hpA), hpE: Math.round(Lv.hpE), z: zoneOf(TEAM[v], vx, vy), vDied, aDied, ek15: enemyDeathsNear(TEAM[v], vx, vy, r, r + 15, 10), h: helpers });
}

// ------------------------------------------------------------------------------------------------ cap: after a gem capture, bank next or keep farming?
const cap = [];
for (const c of caps) {
  if (c.gems <= 0) continue;
  const b = c.b, r = c.r;
  let nxt = 'end', when = -1, bankBag = 0;
  for (let k = r + 1; k <= FR; ++k) {
    if (!alive(b, k)) { nxt = 'died'; when = k - r; break; }
    if (bankR[b][k]) { nxt = 'bank'; when = k - r; bankBag = GM[b][k - 1]; break; }
    if (capR[b][k] > 0) { nxt = 'cap'; when = k - r; break; }
  }
  const L = localState(b, r - 1, 8);
  const tBag = TB[TEAM[b]].reduce((s, u) => s + (alive(u, r) ? GM[u][r] : 0), 0);
  // recall channel running while the capture landed (capture-recall combo), and whether the body went home before the next bag event
  const rcNow = chan[b][r - 1] === 1 || teleR[b][r] ? 1 : 0;
  let viaHome = 0;
  if (when > 0) for (let k = r; k < r + when; ++k) if (alive(b, k) && onSpawn(b, k)) { viaHome = 1; break; }
  const [dn] = nearestEnemy(b, r - 1);
  const row = d.R[Math.min(d.R.length - 1, r)];
  cap.push({ t: TEAM[b], ty: typeId(b), r, gain: c.gems, bag: GM[b][r], tBag, ad: altarD(b, r - 1), hd: homeD(TEAM[b], X[b][r - 1], Y[b][r - 1]), hpf: r2(hpf(b, r - 1)), nE: L.nE, nA: L.nA, dn,
    mhA: Math.round(L.mhA), mhE: Math.round(L.mhE), nxt, when, bankBag, rcNow, viaHome, z: zoneOf(TEAM[b], X[b][r - 1], Y[b][r - 1]), sc: [row[1], row[2]] });
}

// ------------------------------------------------------------------------------------------------ bnk: tribute channels
const bnk = [];
for (const c of tributes) {
  const b = c.b, r = c.r;
  const L = localState(b, r - 1, 8);
  let hitIn = 0, hitters = new Set();
  for (const x of cc) if (x[3] === b && x[1] >= r && x[1] <= c.endR) { hitIn += x[4]; hitters.add(x[2]); }
  // last capture before this tribute: where and when
  let lc = null; for (const k of caps) if (k.b === b && k.r < r && k.gems > 0) lc = k;
  bnk.push({ t: c.t, ty: typeId(b), r, bag: c.bag, dur: c.dur, res: c.res, nE: L.nE, nA: L.nA, dn: nearestEnemy(b, r - 1)[0], hitIn: Math.round(hitIn), nHit: hitters.size,
    hpf: r2(hpf(b, r - 1)), sinceCap: lc ? r - lc.r : -1, capAd: lc ? (() => { const v = AD[Y[b][lc.r] * W + X[b][lc.r]]; return v >= 0 ? v : 999; })() : -1,
    z: zoneOf(c.t, X[b][r], Y[b][r]), died: diesWithin(b, r, c.endR + 1) ? 1 : 0 });
}

// ------------------------------------------------------------------------------------------------ low: health falls below 35% / 20% (crossing)
const low = [];
for (const b of ALLB) for (let r = 2; r <= FR - 1; ++r) {
  if (!alive(b, r) || !alive(b, r - 1) || onSpawn(b, r)) continue;
  for (const T of [0.35, 0.2]) {
    if (!(hpf(b, r) < T && hpf(b, r - 1) >= T)) continue;
    const [dn, e] = nearestEnemy(b, r);
    const L = localState(b, r, 8);
    const wa = windowAct(b, r, 5, e);
    let rcAt = -1; for (const c of recalls) if (c.b === b && c.r > r && c.r <= r + 8 && (c.committed || !spam[TEAM[b]])) { rcAt = c.r - r; break; }
    const rc = rcAt >= 0 ? recalls.find((c) => c.b === b && c.r === r + rcAt) : null;
    const src = tc[b][r] > 0 ? 'champ' : tcamp[b][r] > 0 ? 'camp' : 'other';
    let homeBy = -1; for (let k = r + 1; k <= Math.min(FR, r + 40); ++k) { if (!alive(b, k)) break; if (onSpawn(b, k) || nearSpawn(b, k, 1)) { homeBy = k - r; break; } }
    low.push({ t: TEAM[b], ty: typeId(b), r, T, src, dn, nA: L.nA, nE: L.nE, hpA: Math.round(L.hpA), hpE: Math.round(L.hpE), mhA: Math.round(L.mhA), mhE: Math.round(L.mhE),
      bag: GM[b][r], hd: homeD(TEAM[b], X[b][r], Y[b][r]), busy: busyOf(b, r), a: wa.a, nF: wa.f, dnChg: wa.dn, rcAt, rcRes: rc ? rc.res : null, heal10: Math.round(sumOver(healIn, b, r + 1, r + 10)),
      died15: diesWithin(b, r + 1, r + 15) ? 1 : 0, homeBy, z: zoneOf(TEAM[b], X[b][r], Y[b][r]) });
  }
}

// ------------------------------------------------------------------------------------------------ rcl: recall attempts with context
const rcl = recalls.map((c) => {
  const b = c.b, r = c.r;
  const [dn, e] = nearestEnemy(b, r - 1);
  const L = localState(b, r - 1, 8);
  // did an enemy hit the recaller during the channel? who, how far was it at the start
  const hitters = cc.filter((x) => x[3] === b && x[0] > c.q && x[1] <= (c.done || r + 5)).map((x) => [typeId(x[2]), dist(x[2], r - 1, b, r - 1)]);
  return { t: c.t, ty: typeId(b), r, committed: c.committed, res: c.res, hpf: r2(c.hpf), bag: c.bag, dn, nE: L.nE, nA: L.nA, hd: homeD(c.t, X[b][r], Y[b][r]), hitters, tcPrev: Math.round(sumOver(tc, b, r - 3, r)), spam: spam[c.t] };
});

// ------------------------------------------------------------------------------------------------ omt: fresh outmatched / outmatching states (max health within 8)
const omt = [];
for (const b of ALLB) {
  let lastO = -99, lastU = -99;
  for (let r = 3; r <= FR - 1; ++r) {
    if (!alive(b, r) || onSpawn(b, r)) continue;
    const [dn, e] = nearestEnemy(b, r);
    if (dn > 6) continue;
    const L = localState(b, r, 8);
    const ratio = L.mhA / Math.max(1, L.mhE);
    const under = ratio < 0.7 || L.nE >= L.nA + 2;
    const over = ratio > 1.43 || L.nA >= L.nE + 2;
    if (!under && !over) continue;
    if (under && r - lastU < 12) continue;
    if (over && r - lastO < 12) continue;
    if (under) lastU = r; else lastO = r;
    const wa = windowAct(b, r, 5, e);
    omt.push({ t: TEAM[b], ty: typeId(b), r, kind: under ? 'under' : 'over', ratio: r2(ratio), hpr: r2(L.hpA / Math.max(1, L.hpE)), nA: L.nA, nE: L.nE, dn, hpf: r2(hpf(b, r)), bag: GM[b][r],
      busy: busyOf(b, r), a: wa.a, firstF: wa.firstF, dnChg: wa.dn, died15: diesWithin(b, r + 1, r + 15) ? 1 : 0, ek15: enemyDeathsNear(TEAM[b], X[b][r], Y[b][r], r + 1, r + 15, 10),
      z: zoneOf(TEAM[b], X[b][r], Y[b][r]) });
  }
}

// ------------------------------------------------------------------------------------------------ pun: enemy channels (tribute / committed recall) with our bodies near
const lockEv = d.ev.filter((e) => e.k === 'Place altar lock' && e.who !== undefined);
const pun = [];
const chanList = [
  ...tributes.map((c) => ({ kind: 'trib', b: c.b, t: c.t, r: c.r, end: c.endR, res: c.res, bag: c.bag, dur: c.dur, altar: c.altar })),
  ...recalls.filter((c) => c.committed).map((c) => ({ kind: 'rec', b: c.b, t: c.t, r: c.r, end: c.done || c.r + 5, res: c.res, bag: c.bag, dur: 5 })),
];
for (const c of chanList) {
  const b = c.b, r = c.r;
  const near = TB[1 - c.t].filter((u) => alive(u, r) && !onSpawn(u, r) && dist(u, r, b, r) <= 10);
  if (!near.length) continue;
  const dmin = Math.min(...near.map((u) => dist(u, r, b, r)));
  let dmg = 0, firstHit = -1, stun = 0, lockP = 0;
  const hitters = new Set();
  for (const x of cc) if (x[3] === b && x[1] >= r && x[1] <= c.end && TEAM[x[2]] !== c.t) { dmg += x[4]; hitters.add(x[2]); if (firstHit < 0) firstHit = x[1] - r; }
  for (const s of stunBy) if (s[3] === b && s[1] >= r && s[1] <= c.end && s[2] >= 0 && TEAM[s[2]] !== c.t) stun++;
  if (c.kind === 'trib') for (const l of lockEv) if (TEAM[l.who] !== c.t && l.r >= r && l.r <= c.end && l.to && c.altar && Math.max(Math.abs(l.to[0] - c.altar[0]), Math.abs(l.to[1] - c.altar[1])) === 0) lockP++;
  // did the near bodies move toward the channeller in the window?
  let closer = 0;
  for (const u of near) { const k = Math.min(FR, c.end); if (alive(u, k) && dist(u, k, b, Math.min(k, alive(b, k) ? k : r)) < dist(u, r, b, r)) closer++; }
  pun.push({ t: 1 - c.t, chT: c.t, kind: c.kind, r, dur: c.dur, bag: c.bag, chTy: typeId(b), chHp: r2(hpf(b, r)), n: near.length, dmin, nIn8: near.filter((u) => dist(u, r, b, r) <= 8).length,
    nIn4: near.filter((u) => dist(u, r, b, r) <= 4).length, dmg: Math.round(dmg), nHit: hitters.size, firstHit, stun, lock: lockP, closer, res: c.res, killed: diesWithin(b, r, c.end + 1) ? 1 : 0 });
}

// ------------------------------------------------------------------------------------------------ lck: altar locks placed
const lck = lockEv.map((l) => {
  const t = TEAM[l.who], r = Math.min(l.r, FR);
  const ax = l.to ? l.to[0] : X[l.who][r], ay = l.to ? l.to[1] : Y[l.who][r];
  const enemyTrib = tributes.some((c) => c.t !== t && c.r <= r && c.endR >= r && c.altar && c.altar[0] === ax && c.altar[1] === ay);
  const ownTribSoon = tributes.some((c) => c.t === t && c.r >= r && c.r <= r + 3 && c.altar && c.altar[0] === ax && c.altar[1] === ay);
  const enemyBagNear = TB[1 - t].some((u) => alive(u, r) && GM[u][r] > 0 && Math.max(Math.abs(X[u][r] - ax), Math.abs(Y[u][r] - ay)) <= 4);
  return { t, ty: typeId(l.who), r, cls: enemyTrib ? 'counter' : ownTribSoon ? 'guard' : enemyBagNear ? 'deny' : 'other' };
});

// ------------------------------------------------------------------------------------------------ eng: engagements (champion damage clustered: gap <= 6 rounds, <= 10 tiles)
const engs = [];
const engOfRec = new Map();
for (const x of cc) {
  const r = x[1], v = x[3];
  const pos = alive(v, r) ? [X[v][r], Y[v][r]] : [X[v][r - 1], Y[v][r - 1]];
  let best = null, bd = 99;
  for (let i = engs.length - 1; i >= 0 && i >= engs.length - 6; --i) {
    const g = engs[i];
    if (r - g.r1 > 6) continue;
    const dd = Math.max(Math.abs(pos[0] - g.last[0]), Math.abs(pos[1] - g.last[1]));
    if (dd <= 10 && dd < bd) { bd = dd; best = g; }
  }
  if (!best) { best = { id: engs.length, r0: r, r1: r, c: pos, last: pos, recs: [] }; engs.push(best); }
  best.r1 = r; best.last = pos; best.recs.push(x);
  engOfRec.set(x[0] * 64 + x[3], best.id);
}
const deathEng = new Map(); // death q*64+who -> engagement id
for (const e of deaths) {
  if (typeof e.by !== 'number') continue;
  const id = engOfRec.get(e.q * 64 + e.who);
  if (id !== undefined) deathEng.set(e.q * 64 + e.who, id);
}
const eng = [];
for (const g of engs) {
  const f = g.recs[0];
  const st = TEAM[f[2]];
  const parts = [new Set(), new Set()], dealt = [0, 0], dealt3 = [0, 0], hits = [0, 0], onT = [new Map(), new Map()], casts = [0, 0];
  const dW = [[0, 0, 0], [0, 0, 0]]; // damage by window: r0..r0+2, r0+3..r0+6, r0+7..
  for (const x of g.recs) {
    const ta = TEAM[x[2]];
    parts[ta].add(x[2]); parts[1 - ta].add(x[3]);
    dealt[ta] += x[4]; hits[ta]++;
    dW[ta][x[1] <= g.r0 + 2 ? 0 : x[1] <= g.r0 + 6 ? 1 : 2] += x[4];
    if (x[5] === 6) casts[ta]++;
    if (x[1] <= g.r0 + 2) dealt3[ta] += x[4];
    onT[ta].set(x[3], (onT[ta].get(x[3]) || 0) + x[4]);
  }
  if (g.recs.length < 3 && !deaths.some((e) => deathEng.get(e.q * 64 + e.who) === g.id)) continue;
  const focus = [0, 1].map((t) => (dealt[t] ? r2(Math.max(...onT[t].values()) / dealt[t]) : null));
  // local state at r0 - 1 within 8 of the first victim
  const loc = { n: [0, 0], hp: [0, 0], mh: [0, 0] };
  for (const u of ALLB) { if (!alive(u, g.r0 - 1) || dpt(u, g.r0 - 1, g.c[0], g.c[1]) > 8) continue; if (onSpawn(u, g.r0 - 1)) continue; const t = TEAM[u]; loc.n[t]++; loc.hp[t] += HP[u][g.r0 - 1]; loc.mh[t] += MH[u][g.r0 - 1]; }
  const dE = [0, 0], bag = [0, 0], dTy = [[], []];
  for (const e of deaths) {
    const inE = deathEng.get(e.q * 64 + e.who) === g.id || (e.r >= g.r0 && e.r <= g.r1 + 2 && parts[e.team].has(e.who) && e.by !== 'camp');
    if (inE) { dE[e.team]++; bag[e.team] += e.bag; dTy[e.team].push(TYPE[e.who]); }
  }
  const stun3 = [0, 0];
  for (const s of stunBy) if (s[1] >= g.r0 && s[1] <= g.r0 + 2 && s[2] >= 0 && TEAM[s[2]] !== TEAM[s[3]] && (parts[0].has(s[3]) || parts[1].has(s[3]))) stun3[TEAM[s[2]]]++;
  // first victim's activity in the 3 rounds before
  const v0 = f[3];
  let vFarm = 0, vMove = 0;
  for (let r = g.r0 - 3; r < g.r0; ++r) { vFarm += hcamp[v0][Math.max(0, r)] > 0 ? 1 : 0; vMove += moved(v0, r) ? 1 : 0; }
  // aftermath per team: participants alive at r1 + 1, rounds r1 + 1 .. r1 + 20
  const after = [0, 1].map((t) => {
    const ps = [...parts[t]].filter((b) => alive(b, g.r1 + 1));
    let farm = 0, champ = 0, n = 0, rcl0 = 0, bank = 0, push = 0, reset = 0, caps0 = 0, gemsCap = 0, deadL = 0, theirHalf = 0, toEnemy = 0, toHome = 0;
    for (const b of ps) {
      const k1 = Math.min(FR, g.r1 + 20);
      for (let r = g.r1 + 1; r <= k1; ++r) {
        if (!alive(b, r)) { deadL++; break; }
        n++;
        if (hcamp[b][r] > 0 || capR[b][r]) farm++;
        if (hc[b][r] > 0) champ++;
        if (chan[b][r] === 1) rcl0++;
        if (sub[b][r]) bank++;
        if (zoneOf(t, X[b][r], Y[b][r]) === 2) theirHalf++;
      }
      if (alive(b, k1)) {
        const h0 = homeD(t, X[b][g.r1 + 1], Y[b][g.r1 + 1]), h1 = homeD(t, X[b][k1], Y[b][k1]);
        const e0 = homeD(1 - t, X[b][g.r1 + 1], Y[b][g.r1 + 1]), e1 = homeD(1 - t, X[b][k1], Y[b][k1]);
        if (e1 <= e0 - 4) toEnemy++;
        if (h1 <= h0 - 4 || nearSpawn(b, k1, 2)) toHome++;
      }
    }
    for (const c of caps) if (c.t === t && c.r > g.r1 && c.r <= g.r1 + 30 && ps.includes(c.b)) { caps0++; gemsCap += c.gems; }
    // next engagement started by t within 30 rounds within 15 tiles
    return { n: ps.length, br: n, farm, champ, rcl: rcl0, bank, caps: caps0, gemsCap, deadL, theirHalf, toEnemy, toHome };
  });
  let nextSt = -1, nextDt = -1;
  for (const h of engs) { if (h.id <= g.id || h.r0 <= g.r1 || h.r0 > g.r1 + 30) continue; if (Math.max(Math.abs(h.c[0] - g.c[0]), Math.abs(h.c[1] - g.c[1])) > 15) continue; nextSt = TEAM[h.recs[0][2]]; nextDt = h.r0 - g.r1; break; }
  const d20 = [0, 0];
  for (const e of deaths) if (e.r > g.r1 + 2 && e.r <= g.r1 + 25 && (parts[e.team].has(e.who) || Math.max(Math.abs(e.at[0] - g.c[0]), Math.abs(e.at[1] - g.c[1])) <= 12) && e.by !== 'camp') d20[e.team]++;
  const a0 = f[2];
  const aStill = !moved(a0, g.r0) && !moved(a0, g.r0 - 1) ? 1 : 0;
  const vIn = (alive(v0, g.r0 - 1) && dist(v0, g.r0 - 1, a0, g.r0 - 2) < dist(v0, g.r0 - 2, a0, g.r0 - 2)) || (moved(v0, g.r0) && dist(v0, g.r0, a0, g.r0 - 1) < dist(v0, g.r0 - 1, a0, g.r0 - 1)) ? 1 : 0;
  const aIn = (moved(a0, g.r0) && dist(a0, g.r0, v0, g.r0 - 1) < dist(a0, g.r0 - 1, v0, g.r0 - 1)) || (moved(a0, g.r0 - 1) && dist(a0, g.r0 - 1, v0, g.r0 - 2) < dist(a0, g.r0 - 2, v0, g.r0 - 2)) ? 1 : 0;
  eng.push({ id: g.id, r0: g.r0, r1: g.r1, st, aTy: typeId(f[2]), vTy: typeId(v0), cast: f[5] === 6 ? 1 : 0, vFarm, vMove, vChan: chan[v0][Math.max(0, g.r0 - 1)], aStill, vIn, aIn, dW: dW.map((w) => w.map(Math.round)),
    vHp: r2(hpf(v0, g.r0 - 1)), vBag: GM[v0][Math.max(0, g.r0 - 1)], z0: zoneOf(0, g.c[0], g.c[1]), n: loc.n, hp: loc.hp.map(Math.round), mh: loc.mh.map(Math.round),
    parts: parts.map((s) => s.size), dealt: dealt.map(Math.round), dealt3: dealt3.map(Math.round), hits, casts, focus, stun3, dE, bag, dTy, after, nextSt, nextDt, d20 });
}

// ------------------------------------------------------------------------------------------------ chs: chases
// a chase: within 3 rounds after a hit between a and v (either direction), v steps away from a and a steps after it; continues
// while a keeps closing on v (or holds the gap while v runs) and both are alive and within 10; ends after 2 rounds without that.
const chs = [];
{
  const lastHit = new Map(); // pair a*64+v -> last round with a hit between them
  for (const x of cc) { const k1 = x[2] * 64 + x[3], k2 = x[3] * 64 + x[2]; lastHit.set(k1, Math.max(lastHit.get(k1) || 0, x[1])); lastHit.set(k2, Math.max(lastHit.get(k2) || 0, x[1])); }
  const hitRounds = new Map(); // pair -> sorted rounds
  for (const x of cc) for (const k of [x[2] * 64 + x[3], x[3] * 64 + x[2]]) { if (!hitRounds.has(k)) hitRounds.set(k, []); hitRounds.get(k).push(x[1]); }
  const busyUntil = new Map(); // chaser -> round until which it is already in a chase
  for (const [pk, rs] of hitRounds) {
    const a = Math.floor(pk / 64), v = pk % 64;
    let i = 0;
    while (i < rs.length) {
      const h = rs[i];
      // find the first round k in h+1..h+3 where v moves away from a and a follows
      let k0 = -1;
      for (let k = h + 1; k <= Math.min(FR, h + 3); ++k) {
        if (!alive(a, k) || !alive(v, k) || !alive(a, k - 1) || !alive(v, k - 1)) break;
        const vAway = moved(v, k) && dist(a, k - 1, v, k) > dist(a, k - 1, v, k - 1);
        const aFollow = moved(a, k) && dist(a, k, v, k) < dist(a, k - 1, v, k);
        if (vAway && aFollow) { k0 = k; break; }
      }
      if (k0 < 0 || (busyUntil.get(a) || 0) >= k0) { i++; continue; }
      let k = k0, miss = 0, end = k0, res = 'stop', hitsIn = 0;
      const startHome = homeD(TEAM[a], X[a][k0 - 1], Y[a][k0 - 1]);
      for (k = k0; k <= FR; ++k) {
        if (!alive(v, k)) { res = 'kill'; end = k; break; }
        if (!alive(a, k)) { res = 'chaserDied'; end = k; break; }
        if (dist(a, k, v, k) > 10) { res = 'lost'; end = k; break; }
        if (onSpawn(v, k) || nearSpawn(v, k, 1)) { res = 'home'; end = k; break; }
        if (hc[a][k] > 0 && cc.some((y) => y[1] === k && y[2] === a && y[3] === v)) hitsIn++;
        const follow = moved(a, k) && dist(a, k, v, k) <= dist(a, k - 1, v, k);
        if (follow || (cc.some((y) => y[1] === k && y[2] === a && y[3] === v))) { miss = 0; end = k; } else if (++miss >= 2) break;
      }
      const len = end - k0 + 1;
      busyUntil.set(a, end);
      const endHome = homeD(TEAM[a], X[a][Math.min(FR, end)], Y[a][Math.min(FR, end)]);
      chs.push({ t: TEAM[a], aTy: typeId(a), vTy: typeId(v), r: k0, len, res, hitsIn, aHp: r2(hpf(a, k0 - 1)), vHp: r2(hpf(v, k0 - 1)), z: zoneOf(TEAM[a], X[a][k0], Y[a][k0]),
        deeper: endHome - startHome, aDied10: diesWithin(a, end + 1, end + 10) ? 1 : 0, vDied5: res === 'kill' || diesWithin(v, end + 1, end + 5) ? 1 : 0 });
      while (i < rs.length && rs[i] <= end) i++;
    }
  }
}

// ------------------------------------------------------------------------------------------------ dth: deaths with context
const dth = [];
for (const e of deaths) {
  const v = e.who, t = e.team, r = e.r;
  const pos = e.at;
  // damage sequence start
  let s = r;
  for (let k = r; k >= Math.max(1, r - 40); --k) { if (tc[v][k] > 0 || tcamp[v][k] > 0) s = k; else if (s - k > 4) break; }
  const act = [];
  for (let k = r - 9; k <= r; ++k) {
    if (k < 1) continue;
    let a = '';
    if (hc[v][k] > 0) a += 'F';
    if (hcamp[v][k] > 0) a += 'C';
    if (chan[v][k] === 1) a += 'R';
    if (chan[v][k] === 2) a += 'B';
    if (moved(v, k)) { const [n0] = nearestEnemyAt(v, k - 1, X[v][k - 1], Y[v][k - 1]); const [n1] = nearestEnemyAt(v, k - 1, X[v][k], Y[v][k]); a += n1 < n0 ? 'a' : n1 > n0 ? 'w' : 'm'; }
    if (stunIn[v][k]) a += 's';
    if (!a) a = '.';
    act.push(a);
  }
  const last3 = act.slice(-3).join(''), last5 = act.slice(-5).join('');
  let mode;
  if (e.by === 'camp') mode = cc.some((x) => x[3] === v && x[1] >= s && x[1] <= r) ? 'campContested' : 'camp';
  else if (/B/.test(last3)) mode = 'banking';
  else if (/R/.test(last5)) mode = 'recalling';
  else if (/F/.test(last3)) mode = 'fighting';
  else if (/C/.test(last3)) mode = 'farming';
  else {
    const aw = (last5.match(/w/g) || []).length, ap = (last5.match(/a/g) || []).length;
    mode = aw > ap ? (/F/.test(act.join('')) ? 'fleeAfterFight' : 'flee') : ap > aw ? 'approach' : 'walk';
  }
  const L6 = localStateAt(t, pos, r - 1, 6, v), L8 = localStateAt(t, pos, r - 1, 8, v);
  const atk = new Map();
  for (const x of cc) if (x[3] === v && x[1] >= s && x[1] <= r) atk.set(x[2], (atk.get(x[2]) || 0) + x[4]);
  const atkMh = [...atk.keys()].map((b) => MH[b][r - 1]);
  let own8 = 0; for (const x of cc) if (x[2] === v && x[1] >= r - 8 && x[1] <= r) own8 += x[4];
  let expo = 0; for (let k = r - 1; k >= Math.max(1, r - 60); --k) { if (!alive(v, k) || nearestEnemy(v, k)[0] > 8) break; expo++; }
  const trade = deaths.filter((x) => x.team !== t && Math.abs(x.r - r) <= 6 && Math.max(Math.abs(x.at[0] - pos[0]), Math.abs(x.at[1] - pos[1])) <= 10).length;
  const eid = deathEng.get(e.q * 64 + v);
  const eg = eid !== undefined ? engs[eid] : null;
  dth.push({ t, ty: TYPE[v], r, by: typeof e.by === 'number' ? TYPE[e.by] : String(e.by), bag: e.bag, mode, act: act.join(' '), z: zoneOf(t, pos[0], pos[1]), hd: homeD(t, pos[0], pos[1]),
    hpS: r2(hpf(v, s - 1)), seq: r - s, mh: Math.round(MH[v][r - 1]), atkMh, natk: atk.size, nA6: L6.nA, nE6: L6.nE, nA8: L8.nA, nE8: L8.nE, mhA8: Math.round(L8.mhA), mhE8: Math.round(L8.mhE),
    own8: Math.round(own8), expo, trade, engSt: eg ? TEAM[eg.recs[0][2]] : -1, engR0: eg ? eg.r0 : -1 });
}
function nearestEnemyAt(b, r, x, y) { let m = 99; for (const e of TB[1 - TEAM[b]]) if (enemyOK(e, r)) m = Math.min(m, dpt(e, r, x, y)); return [m]; }
function localStateAt(t, pos, r, R, skip) {
  const o = { nA: 0, nE: 0, mhA: 0, mhE: 0 };
  for (const u of ALLB) { if (u === skip || !alive(u, r) || dpt(u, r, pos[0], pos[1]) > R) continue; if (TEAM[u] === t) { o.nA++; o.mhA += MH[u][r]; } else if (!onSpawn(u, r)) { o.nE++; o.mhE += MH[u][r]; } }
  return o;
}

// ------------------------------------------------------------------------------------------------ ctc: fresh contacts (opposing bodies within 5; no champion damage within 10 tiles for 8 rounds)
const ctc = [];
{
  let hi0 = 0;
  const hitPos = cc.map((x) => { const v = x[3], r = x[1]; return [r, alive(v, r) ? X[v][r] : X[v][r - 1], alive(v, r) ? Y[v][r] : Y[v][r - 1], TEAM[x[2]], x[2], v, x[5]]; });
  for (let r = 2; r <= FR - 1; ++r) {
    while (hi0 < hitPos.length && hitPos[hi0][0] < r - 8) hi0++;
    for (const a of TB[0]) {
      if (!enemyOK(a, r)) continue;
      for (const b of TB[1]) {
        if (!enemyOK(b, r) || dist(a, r, b, r) > 5) continue;
        const m = [Math.round((X[a][r] + X[b][r]) / 2), Math.round((Y[a][r] + Y[b][r]) / 2)];
        let busy = false;
        for (let i = hi0; i < hitPos.length && hitPos[i][0] < r; ++i) if (Math.max(Math.abs(hitPos[i][1] - m[0]), Math.abs(hitPos[i][2] - m[1])) <= 10) { busy = true; break; }
        if (busy || ctc.some((c) => r - c.r <= 8 && Math.max(Math.abs(c.m[0] - m[0]), Math.abs(c.m[1] - m[1])) <= 10)) continue;
        let first = null;
        for (let i = hi0; i < hitPos.length && hitPos[i][0] <= r + 5; ++i) { const h = hitPos[i]; if (h[0] < r) continue; if (Math.max(Math.abs(h[1] - m[0]), Math.abs(h[2] - m[1])) <= 10) { first = h; break; } }
        const loc = { n: [0, 0], hp: [0, 0], mh: [0, 0] };
        for (const u of ALLB) { if (!enemyOK(u, r) || Math.max(Math.abs(X[u][r] - m[0]), Math.abs(Y[u][r] - m[1])) > 8) continue; const t = TEAM[u]; loc.n[t]++; loc.hp[t] += HP[u][r]; loc.mh[t] += MH[u][r]; }
        // who closed the gap in the last 2 rounds: a's and b's own moves
        const aIn = dist(a, r, b, r - 1) < dist(a, r - 1, b, r - 1) ? 1 : 0, bIn = dist(b, r, a, r - 1) < dist(b, r - 1, a, r - 1) ? 1 : 0;
        ctc.push({ r, m, d: dist(a, r, b, r), first: first ? first[3] : -1, dt: first ? first[0] - r : -1, fCast: first ? (first[6] === 6 ? 1 : 0) : -1, fTy: first ? TYPE[first[4]] : null,
          n: loc.n, hp: loc.hp.map(Math.round), mh: loc.mh.map(Math.round), inMove: [aIn, bIn], farm: [hcamp[a][r] > 0 ? 1 : 0, hcamp[b][r] > 0 ? 1 : 0], z0: zoneOf(0, m[0], m[1]) });
      }
    }
  }
}

// ------------------------------------------------------------------------------------------------ per-team summary
const sum = [0, 1].map((t) => {
  const o = { deaths: 0, campDeaths: 0, kills: 0, bagLost: 0, bagStolen: 0, banked: 0, banks: 0, maxBag: 0, dmgOut: 0, dmgIn: 0, campIn: 0, rcAtt: 0, rcDone: 0, rcInt: 0, rcKilled: 0,
    tribs: 0, tribDone: 0, tribKilled: 0, tribStun: 0, tribLock: 0, locks: 0, spam: spam[t], mh300: 0, mh600: 0, sub: d.R[d.R.length - 1][1 + t] };
  for (const e of deaths) { if (e.team === t) { o.deaths++; o.bagLost += e.bag; if (e.by === 'camp') o.campDeaths++; } else if (typeof e.by === 'number' && TEAM[e.by] === t) { o.kills++; o.bagStolen += e.bag; } }
  for (const e of banksEv) if (TEAM[e.who] === t) o.banks++;
  for (const e of d.ev) if (e.k === 'Banked' && e.team === t) o.banked += e.gems;
  for (const b of TB[t]) { for (let r = 1; r <= FR; ++r) o.maxBag = Math.max(o.maxBag, GM[b][r]); o.dmgOut += hc[b].reduce((a, v) => a + v, 0); o.dmgIn += tc[b].reduce((a, v) => a + v, 0); o.campIn += tcamp[b].reduce((a, v) => a + v, 0); o.mh300 += MH[b][Math.min(FR, 300)]; o.mh600 += MH[b][Math.min(FR, 600)]; }
  for (const c of recalls) if (c.t === t && c.committed) { o.rcAtt++; if (c.res === 'done') o.rcDone++; else if (c.res === 'interrupted') o.rcInt++; else if (c.res === 'killed') o.rcKilled++; }
  for (const c of tributes) if (c.t === t) { o.tribs++; if (c.res === 'done') o.tribDone++; else if (c.res === 'killed') o.tribKilled++; else if (c.res === 'stunned') o.tribStun++; else if (c.res === 'locked') o.tribLock++; }
  for (const l of lck) if (l.t === t) o.locks++;
  o.dmgOut = Math.round(o.dmgOut); o.dmgIn = Math.round(o.dmgIn); o.campIn = Math.round(o.campIn); o.mh300 = Math.round(o.mh300); o.mh600 = Math.round(o.mh600);
  return o;
});

console.log(JSON.stringify({ ...out0, map: SD.map, st: SD.st, win: SD.win, opp: SD.opp, FR, outcome: d.meta.outcome, W, H, nb: [TB[0].length, TB[1].length], types: [TB[0].map(typeId), TB[1].map(typeId)],
  sum, smp, arr, ast, cap, bnk, low, rcl, omt, pun, lck, eng, chs, dth, ctc }));
