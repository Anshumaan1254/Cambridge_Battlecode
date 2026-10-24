#!/usr/bin/env node
// Fight analysis over tools/live/fightdump.mjs dumps (exact per-step damage attribution). One JSON line per game:
//   deaths[]   every champion death: what the victim did in the 10 rounds before (activity by round), local numbers / health within
//              6 and 8 (1 and 5 rounds before and at the start of its damage sequence), bag, zone (own / mid / their half, near their
//              spawn), killer type, distinct attackers, allies within 8 that did not hit, the engagement it belongs to (who started).
//   engs[]     engagements = champion-vs-champion damage clustered in time (gap <= 6 rounds) and space (<= 10 tiles): first hit
//              (team, champion, cast / attack, stun), state at the start (bodies, health, max health within 8), bodies brought by
//              r0+5, damage in the first 3 rounds, focus (damage share on the most-damaged target), casts and stuns at the start,
//              spells ready / burned on camps before, deaths in the engagement and within 20 rounds, aftermath per side.
//   contacts[] fresh contacts (opposing bodies within 4 tiles, no champion damage within 10 tiles for 8 rounds): who hits first
//              within 5 rounds (or nobody) and the local power at contact.
// Usage: node tools/live/fightan.mjs SIDES.json DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const [sidesFile, file] = process.argv.slice(2);
const sides = JSON.parse(fs.readFileSync(sidesFile, 'utf8'));
const name = path.basename(file).replace(/\.json\.gz$/, '');
const S = sides[name] || {};
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: name, err: String(e) })); process.exit(0); }
const FR = d.meta.finalRound;
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const NB = Math.max(...d.meta.bodies.map((b) => b.index)) + 1;
const teamOf = (i) => B.get(i).team;
const typeOf = (i) => B.get(i).type;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

// ST[r][body] = [x, y, hp, maxHp, alive, gems, gold, stunned] at the end of round r
const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) {
  const row = d.R[i];
  const r = row[0];
  if (r < 1 || r > FR) continue;
  const a = new Array(NB);
  for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[9]];
  ST[r] = a;
}
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const bodiesOf = (t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index);
const TB = [bodiesOf(0), bodiesOf(1)];
// spawn centres: initial positions
const spawnC = [0, 1].map((t) => {
  const ps = TB[t].map((b) => P(1, b));
  return [Math.round(ps.reduce((s, p) => s + p[0], 0) / ps.length), Math.round(ps.reduce((s, p) => s + p[1], 0) / ps.length)];
});
const campTiles = new Set(d.meta.camps.map((c) => c.x * 1000 + c.y));
const zoneOf = (p, t) => {
  const a = cheb(p, spawnC[t]), b = cheb(p, spawnC[1 - t]);
  const f = a / Math.max(1, a + b);
  return { zone: f < 0.4 ? 'own' : f > 0.6 ? 'their' : 'mid', frac: +f.toFixed(2), dOwn: a, dTheir: b };
};

// per body per round activity
const mk = (T) => Array.from({ length: NB }, () => new T(FR + 3));
const hc = mk(Float32Array), tc = mk(Float32Array), hcamp = mk(Float32Array), tcamp = mk(Float32Array);
const rec = mk(Uint8Array), sub = mk(Uint8Array), castN = mk(Uint8Array), castCamp = mk(Uint8Array), stunned = mk(Uint8Array);
const castLog = Array.from({ length: NB }, () => []); // [r, slot]
const ccDmg = d.dmg.filter((x) => x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])); // champion on enemy champion
const reflect = d.dmg.filter((x) => x[2] >= 0 && x[2] === x[3]);
for (const x of ccDmg) { hc[x[2]][x[1]] += x[4]; tc[x[3]][x[1]] += x[4]; }
for (const x of d.dmg) if (x[2] < 0) tcamp[x[3]][x[1]] += x[4];
for (const x of d.cdmg) hcamp[x[2]][x[1]] += x[4];
const campCastQ = new Set(d.cdmg.map((x) => x[0] * 64 + x[2]));
const champCastQ = new Set(ccDmg.filter((x) => x[5] === 6).map((x) => x[0] * 64 + x[2]));
for (const e of d.ev) {
  if (e.who === undefined || e.r > FR + 1) continue;
  if (e.k === 'Recall') rec[e.who][e.r] = 1;
  else if (e.k === 'Submit gems') sub[e.who][e.r] = 1;
  else if (e.k === 'Cast ability') {
    castN[e.who][e.r]++;
    castLog[e.who].push([e.r, e.slot, e.q]);
    if (campCastQ.has(e.q * 64 + e.who) && !champCastQ.has(e.q * 64 + e.who)) castCamp[e.who][e.r]++;
  }
}
for (const x of d.stun) if (x[3] >= 0 && x[3] < NB) stunned[x[3]][x[1]] = 1;
const moved = (b, r) => { const a = P(r - 1, b), c = P(r, b); return a && c && a[4] && c[4] && (a[0] !== c[0] || a[1] !== c[1]); };
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const nearestEnemyD = (r, b, pos) => {
  let m = 99;
  for (const e of TB[1 - teamOf(b)]) { const q = P(r, e); if (q && q[4]) m = Math.min(m, cheb(pos, q)); }
  return m;
};
const local = (r, pos, t, R, skip = -1) => {
  const o = { n: [0, 0], hp: [0, 0], mh: [0, 0] }; // [team t, other]
  for (let b = 0; b < NB; ++b) {
    if (!B.has(b) || b === skip) continue;
    const p = P(r, b);
    if (!p || !p[4] || cheb(p, pos) > R) continue;
    const k = teamOf(b) === t ? 0 : 1;
    o.n[k]++; o.hp[k] += p[2]; o.mh[k] += p[3];
  }
  return o;
};
const ready = (b, r, slot) => { // slot cast at least 8 rounds before r (cooldown 8 owner turn ends), or never
  let last = -99;
  for (const c of castLog[b]) { if (c[0] >= r) break; if (c[1] === slot) last = c[0]; }
  return r - last >= 8;
};

// ---------------------------------------------------------------- engagements
const engs = [];
const sorted = ccDmg.slice().sort((a, b) => a[0] - b[0]);
const recOf = new Map(); // dmg record q*64+victim -> engagement id
for (const x of sorted) {
  const r = x[1];
  const vp = P(r, x[3]) && P(r, x[3])[4] ? P(r, x[3]) : P(r - 1, x[3]);
  const pos = [vp[0], vp[1]];
  let best = null, bd = 99;
  for (let i = engs.length - 1; i >= 0 && i >= engs.length - 6; --i) {
    const g = engs[i];
    if (r - g.r1 > 6) continue;
    const dd = cheb(pos, g.last);
    if (dd <= 10 && dd < bd) bd = dd, best = g;
  }
  if (!best) {
    best = { id: engs.length, r0: r, r1: r, q0: x[0], c: pos, last: pos, recs: [] };
    engs.push(best);
  }
  best.r1 = r; best.last = pos; best.recs.push(x);
  recOf.set(x[0] * 64 + x[3], best.id);
}
const deathsAll = d.ev.filter((e) => e.k === 'Death');
const deathQ = new Map(deathsAll.map((e) => [e.q * 64 + e.who, e]));
const engOut = [];
for (const g of engs) {
  const f = g.recs[0];
  const st = teamOf(f[2]);
  const parts = [new Set(), new Set()];
  const parts5 = [new Set(), new Set()];
  const dealt = [0, 0], dealt3 = [0, 0], hits = [0, 0], castHits = [0, 0], castHits3 = [0, 0];
  const onT = [new Map(), new Map()];
  for (const x of g.recs) {
    const ta = teamOf(x[2]);
    parts[ta].add(x[2]); parts[1 - ta].add(x[3]);
    if (x[1] <= g.r0 + 5) { parts5[ta].add(x[2]); parts5[1 - ta].add(x[3]); }
    dealt[ta] += x[4]; hits[ta]++;
    if (x[5] === 6) castHits[ta]++;
    if (x[1] <= g.r0 + 2) { dealt3[ta] += x[4]; if (x[5] === 6) castHits3[ta]++; }
    onT[ta].set(x[3], (onT[ta].get(x[3]) || 0) + x[4]);
  }
  const focus = [0, 1].map((t) => dealt[t] ? +(Math.max(...onT[t].values()) / dealt[t]).toFixed(2) : null);
  const stuns3 = [0, 0];
  for (const s of d.stun) if (s[1] >= g.r0 && s[1] <= g.r0 + 2 && s[2] >= 0 && s[3] >= 0 && cheb(P(s[1], s[3]), g.c) <= 10 && teamOf(s[2]) !== teamOf(s[3])) stuns3[teamOf(s[2])]++;
  const loc0 = local(g.r0 - 1, g.c, st, 8);
  const loc0b = local(g.r0 - 1, g.c, st, 5);
  // deaths: in the engagement (r0 .. r1 + 2, participants or within 10 of the centre), and within 20 rounds of the start among
  // bodies involved in the first 5 rounds
  const dE = [0, 0], d20 = [0, 0], bag = [0, 0];
  for (const e of deathsAll) {
    const t = e.team;
    const inv = parts[t].has(e.who) || cheb(e.at, g.c) <= 10 || cheb(e.at, g.last) <= 10;
    if (e.r >= g.r0 && e.r <= g.r1 + 2 && inv) { dE[t]++; bag[t] += e.bag; }
    if (e.r >= g.r0 && e.r <= g.r0 + 20 && (parts5[t].has(e.who) || (cheb(e.at, g.c) <= 10 && e.by !== 'camp'))) d20[t]++;
  }
  // what the first victim was doing (3 rounds before r0)
  const v0 = f[3];
  let vFarm = 0, vMove = 0, vChan = 0;
  for (let r = g.r0 - 3; r < g.r0; ++r) { vFarm += hcamp[v0][r] > 0; vMove += moved(v0, r) ? 1 : 0; vChan += rec[v0][r] + sub[v0][r]; }
  // spells: ready slots among the bodies within 8 at the start, casts on camps in the 8 rounds before
  const rdy = [0, 0], burned = [0, 0], nb8 = [0, 0];
  for (let b = 0; b < NB; ++b) {
    if (!B.has(b) || !alive(g.r0 - 1, b) || cheb(P(g.r0 - 1, b), g.c) > 8) continue;
    const t = teamOf(b);
    nb8[t]++;
    rdy[t] += (ready(b, g.r0, 0) ? 1 : 0) + (ready(b, g.r0, 1) ? 1 : 0);
    for (let r = g.r0 - 8; r < g.r0; ++r) burned[t] += castCamp[b][Math.max(0, r)];
  }
  // aftermath per side: participants alive at r1 + 1, rounds r1 + 1 .. r1 + 15
  const after = [0, 1].map((t) => {
    const ps = [...parts[t]].filter((b) => alive(g.r1 + 1, b));
    let farm = 0, champ = 0, mv = 0, home = 0, recall = 0, bank = 0, still = 0, n = 0, caps = 0, toward = 0;
    for (const b of ps) for (let r = g.r1 + 1; r <= Math.min(FR, g.r1 + 15); ++r) {
      if (!alive(r, b)) continue;
      ++n;
      if (hcamp[b][r] > 0) farm++;
      if (hc[b][r] > 0) champ++;
      if (rec[b][r]) recall++;
      if (sub[b][r]) bank++;
      if (moved(b, r)) {
        mv++;
        const a = P(r - 1, b), c = P(r, b);
        if (cheb(c, spawnC[t]) < cheb(a, spawnC[t])) home++;
        const ne0 = nearestEnemyD(r - 1, b, a), ne1 = nearestEnemyD(r - 1, b, c);
        if (ne1 < ne0) toward++;
      } else if (!(hcamp[b][r] > 0) && !(hc[b][r] > 0)) still++;
    }
    for (const e of d.ev) if (e.k === 'CaptureGems' && e.team === t && e.r > g.r1 && e.r <= g.r1 + 20 && ps.includes(e.who)) caps++;
    return { n: ps.length, br: n, farm, champ, mv, home, toward, recall, bank, still, caps };
  });
  engOut.push({
    id: g.id, r0: g.r0, r1: g.r1, c: g.c, zone0: zoneOf(g.c, 0).zone, frac0: zoneOf(g.c, 0).frac,
    first: { team: st, a: typeOf(f[2]), v: typeOf(f[3]), cast: f[5] === 6 ? 1 : 0, slot: f[6], dmg: f[4], vFarm, vMove, vChan, vHp: P(g.r0 - 1, v0) ? +(P(g.r0 - 1, v0)[2] / P(g.r0 - 1, v0)[3]).toFixed(2) : null },
    n8: nb8, loc8: loc0, loc5: loc0b, // loc: [starter side, other side]
    parts: parts.map((s) => s.size), parts5: parts5.map((s) => s.size), dealt, dealt3, hits, castHits, castHits3, stuns3, focus,
    attackers: [0, 1].map((t) => new Set(g.recs.filter((x) => teamOf(x[2]) === t).map((x) => x[2])).size),
    rdy, burned, dE, d20, bag, after,
  });
}

// ---------------------------------------------------------------- deaths
const deaths = [];
for (const e of deathsAll) {
  const v = e.who, t = e.team, r = e.r;
  const killDmg = d.dmg.find((x) => x[0] === e.q && x[3] === v);
  const linked = !killDmg; // Cassi / Issac partner dying with the other
  const pre = P(r - 1, v);
  const pos = e.at;
  const z = zoneOf(pos, t);
  // damage sequence start: rounds with champion damage taken, gaps <= 4
  let s = r;
  for (let k = r; k >= Math.max(1, r - 40); --k) { if (tc[v][k] > 0 || tcamp[v][k] > 0) s = k; else if (s - k > 4) break; }
  const ps = P(s - 1, v);
  const act = [];
  for (let k = r - 9; k <= r; ++k) {
    if (k < 1) continue;
    let a = '';
    if (hc[v][k] > 0) a += 'F';
    if (hcamp[v][k] > 0) a += 'C';
    if (rec[v][k]) a += 'R';
    if (sub[v][k]) a += 'B';
    if (moved(v, k)) {
      const p0 = P(k - 1, v), p1 = P(k, v);
      const ne0 = nearestEnemyD(k - 1, v, p0), ne1 = nearestEnemyD(k - 1, v, p1);
      a += ne1 < ne0 ? 'a' : ne1 > ne0 ? 'w' : 'm'; // approach / away / sideways
    }
    if (stunned[v][k]) a += 's';
    if (!a) a = campTiles.has(P(k, v)[0] * 1000 + P(k, v)[1]) ? 'k' : '.'; // standing on a camp tile / idle
    act.push(a);
  }
  const last3 = act.slice(-3).join(''), last5 = act.slice(-5).join(''), first5 = act.slice(0, 5).join('');
  let mode;
  if (linked) mode = 'linked';
  else if (e.by === 'camp') mode = 'camp';
  else if (/B/.test(last3)) mode = 'banking';
  else if (/R/.test(last5)) mode = 'recalling';
  else if (/F/.test(last3)) mode = 'fighting';
  else if (/C/.test(last3)) mode = 'farming';
  else if (/k/.test(last3) && !/[awm]/.test(last3)) mode = 'capturing';
  else {
    const aw = (last5.match(/w/g) || []).length, ap = (last5.match(/a/g) || []).length;
    mode = aw > ap ? 'fleeing' : ap > aw ? 'approaching' : /s/.test(last3) ? 'stunned' : 'walking';
  }
  const fightBefore = /F/.test(first5) || /F/.test(act.slice(0, 7).join(''));
  const l6 = local(r - 1, pos, t, 6), l8 = local(r - 1, pos, t, 8), l8s = local(s - 1, ps ? [ps[0], ps[1]] : pos, t, 8), l8_5 = local(r - 5, P(r - 5, v) ? [P(r - 5, v)[0], P(r - 5, v)[1]] : pos, t, 8);
  // attackers in the sequence
  const atk = new Map();
  for (const x of ccDmg) if (x[3] === v && x[1] >= s && x[1] <= r) atk.set(x[2], (atk.get(x[2]) || 0) + x[4]);
  const campTaken = d.dmg.filter((x) => x[2] < 0 && x[3] === v && x[1] >= s && x[1] <= r).reduce((a, x) => a + x[4], 0);
  // allies within 8 at r-1: did they hit an enemy champion in r-5..r?
  const allies = [];
  for (const b of TB[t]) {
    if (b === v || !alive(r - 1, b) || cheb(P(r - 1, b), pos) > 8) continue;
    let h = 0, f = 0, ch = 0, m = 0;
    for (let k = r - 5; k <= r; ++k) { h += hc[b][k]; f += hcamp[b][k] > 0; ch += rec[b][k] + sub[b][k]; m += moved(b, k) ? 1 : 0; }
    allies.push({ d: cheb(P(r - 1, b), pos), hit: h > 0 ? 1 : 0, farm: f, chan: ch, mv: m, hpf: +(P(r - 1, b)[2] / P(r - 1, b)[3]).toFixed(2) });
  }
  // victim's own damage in the 10 rounds before, and on its killer
  let own = 0, onKiller = 0;
  for (const x of ccDmg) if (x[2] === v && x[1] >= r - 10 && x[1] <= r) { own += x[4]; if (x[3] === e.by) onKiller += x[4]; }
  const kp = typeof e.by === 'number' ? P(r, e.by) : null;
  // enemy within 8 for how long before death (exposure)
  let expo = 0;
  for (let k = r - 1; k >= Math.max(1, r - 40); --k) { const p = P(k, v); if (!p || !p[4] || nearestEnemyD(k, v, p) > 8) break; expo++; }
  // a trade: an enemy death within 10 tiles in r-5 .. r+5
  const trade = deathsAll.filter((x) => x.team !== t && Math.abs(x.r - r) <= 5 && cheb(x.at, pos) <= 10).length;
  const engId = killDmg ? recOf.get(killDmg[0] * 64 + v) : undefined;
  const eg = engId !== undefined ? engOut[engId] : null;
  deaths.push({
    r, team: t, v: typeOf(v), by: typeof e.by === 'number' ? typeOf(e.by) : e.by, bag: e.bag, mode, act: act.join(' '), fightBefore: fightBefore ? 1 : 0,
    zone: z.zone, frac: z.frac, dTheir: z.dTheir, dOwn: z.dOwn,
    hp1: pre ? +(pre[2] / pre[3]).toFixed(2) : null, mh: pre ? pre[3] : null, hpS: ps ? +(ps[2] / ps[3]).toFixed(2) : null, seq: r - s,
    l6, l8, l8s, l8_5, natk: atk.size, atkMh: [...atk.keys()].map((b) => P(r - 1, b) ? P(r - 1, b)[3] : 0), campTaken,
    allies, own: Math.round(own), onKiller: Math.round(onKiller), killerHp: kp ? +(kp[2] / kp[3]).toFixed(2) : null, expo, trade,
    eng: eg ? { id: eg.id, st: eg.first.team, r0: eg.r0, dE: eg.dE } : null,
  });
}

// ---------------------------------------------------------------- contacts (take / avoid)
const contacts = [];
const hitIdx = sorted.map((x) => { const p = P(x[1], x[3]) && P(x[1], x[3])[4] ? P(x[1], x[3]) : P(x[1] - 1, x[3]); return [x[1], p[0], p[1], teamOf(x[2]), x[0], x[2], x[3]]; });
let hi0 = 0;
for (let r = 2; r <= FR; ++r) {
  while (hi0 < hitIdx.length && hitIdx[hi0][0] < r - 8) hi0++;
  for (const a of TB[0]) {
    const pa = P(r, a);
    if (!pa || !pa[4]) continue;
    for (const b of TB[1]) {
      const pb = P(r, b);
      if (!pb || !pb[4] || cheb(pa, pb) > 4) continue;
      const m = [Math.round((pa[0] + pb[0]) / 2), Math.round((pa[1] + pb[1]) / 2)];
      let busy = false;
      for (let i = hi0; i < hitIdx.length && hitIdx[i][0] < r; ++i) if (cheb([hitIdx[i][1], hitIdx[i][2]], m) <= 10) { busy = true; break; }
      if (busy) continue;
      if (contacts.some((c) => r - c.r <= 8 && cheb(c.m, m) <= 10)) continue;
      // previous round: was this pair already within 4? (then not fresh unless the area was busy, skip)
      const pa0 = P(r - 1, a), pb0 = P(r - 1, b);
      if (pa0 && pb0 && pa0[4] && pb0[4] && cheb(pa0, pb0) <= 4 && r > 2) {
        // pair standing within 4 without fighting: still record once per episode (handled by the episode check above)
      }
      let first = null;
      for (let i = hi0; i < hitIdx.length && hitIdx[i][0] <= r + 5; ++i) {
        const h = hitIdx[i];
        if (h[0] < r) continue;
        if (cheb([h[1], h[2]], m) <= 10) { first = h; break; }
      }
      const l = local(r, m, 0, 8);
      const busyA = [0, 1].map((t) => { let f = 0; const bb = t === 0 ? a : b; for (let k = r - 2; k <= r; ++k) f += hcamp[bb][k] > 0 ? 1 : 0; return f; });
      contacts.push({ r, m, a: typeOf(a), b: typeOf(b), dist: cheb(pa, pb), first: first ? first[3] : -1, dt: first ? first[0] - r : null, n: l.n, hp: l.hp, mh: l.mh,
        hpf: [+(pa[2] / pa[3]).toFixed(2), +(pb[2] / pb[3]).toFixed(2)], farm: busyA, zone0: zoneOf(m, 0).zone });
    }
  }
}

console.log(JSON.stringify({ file: path.basename(file), game: name, set: S.set, ours: S.ours ?? null, names: S.names, res: S.res, map: S.map, outcome: d.meta.outcome, FR, spawnC, deaths, engs: engOut, contacts }));
