#!/usr/bin/env node
// Weakness extraction (an_weak): one JSON line per tools/live/fightdump.mjs dump of a study-team game, metrics for the study team (T[0])
// and its opponent (T[1]): banked curve, captures by zone/class, deaths with context (zone, bag, killer, isolation, chase), tribute
// episodes (bag, length, outcome: done / death / stun / lock / self, enemies near), altar locks (did they cancel a tribute), idle runs,
// completed recalls, cohesion (largest cluster), raids (captures on the other team's own zone, defended or not), carry stats per body.
//   node tools/top2/weak/wx.mjs C:/battlecode/cache/t2dump/<key>/<map>_<mid8>.json.gz ...
// Study team = the team of C:/battlecode/cache/t2/<key>/index.jsonl (side a = team 0). Zones by walking distance (mapgeo2.jsonl):
// f = d_own / (d_own + d_enemy): own < 0.4, mid 0.4-0.6, enemy > 0.6.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
const GEO = new Map();
for (const l of fs.readFileSync(process.env.MAPGEO || 'C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n')) {
  if (!l.trim()) continue; const g = JSON.parse(l); GEO.set(g.map, g);
}
const IDX = new Map();
function idx(key) {
  if (IDX.has(key)) return IDX.get(key);
  const m = new Map();
  const p = `C:/battlecode/cache/t2/${key}/index.jsonl`;
  if (fs.existsSync(p)) for (const l of fs.readFileSync(p, 'utf8').split('\n')) { if (!l.trim()) continue; const r = JSON.parse(l); m.set(r.matchId.slice(0, 8), r); }
  IDX.set(key, m); return m;
}
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
const CP = [100, 150, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000];
const STUNNERS = new Set(['Prism', 'Ryth', 'Marcella', 'Tavi', 'Cassi', 'HeartOfRuin', 'Ren']);

for (const file of process.argv.slice(2)) {
  const base = path.basename(file);
  const key = path.basename(path.dirname(file));
  const mm = base.match(/^(.*)_([0-9a-f]{8})\.json\.gz$/);
  if (!mm) continue;
  const map = mm[1], mid8 = mm[2];
  let d;
  try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: base, err: 'read ' + e.message })); continue; }
  const row = idx(key).get(mid8);
  if (!row) { console.log(JSON.stringify({ file: base, err: 'no index row' })); continue; }
  const tid = TEAMS[key];
  const me = row.teams.find((t) => t.teamId.startsWith(tid)), op = row.teams.find((t) => !t.teamId.startsWith(tid));
  const S = me.side === 'a' ? 0 : 1, O = 1 - S;
  const geo = GEO.get(map);
  if (!geo) { console.log(JSON.stringify({ file: base, err: 'no geo ' + map })); continue; }
  const W = geo.W, H = geo.H;
  const bodies = d.meta.bodies;
  const teamOf = (i) => bodies[i]?.team;
  const tyOf = (i) => bodies[i]?.type;
  // rounds: last entry with a given round number wins (the first R entry is the initial state)
  const RS = new Map();
  for (const e of d.R) RS.set(e[0], e);
  const final = d.meta.finalRound;
  const pos = (r, i) => { const e = RS.get(r); if (!e) return null; for (const c of e[3]) if (c[0] === i) return c; return null; };
  const PM = new Map(); // r -> Map(i -> c)
  for (const [r, e] of RS) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(r, m); }
  const P = (r, i) => PM.get(r)?.get(i) || null;
  // spawn centres from round 1 (check against geo spawnA)
  const r1 = PM.get(1) || PM.get(2);
  const sc = [0, 1].map((t) => { const b = [...r1.values()].filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
  const gA = geo.spawnA.reduce((a, c) => [a[0] + c[0] / geo.spawnA.length, a[1] + c[1] / geo.spawnA.length], [0, 0]);
  const swap = cheb(sc[0][0], sc[0][1], gA[0], gA[1]) > cheb(sc[1][0], sc[1][1], gA[0], gA[1]);
  const dOwn = (t, x, y) => { if (x < 0 || y < 0 || x >= W || y >= H) return null; const a = geo.dA[y * W + x], b = geo.dB[y * W + x]; if (a < 0 || b < 0) return null; return ((t === 0) !== swap) ? a : b; };
  const dEn = (t, x, y) => dOwn(1 - t, x, y);
  const fOf = (t, x, y) => { const a = dOwn(t, x, y), b = dEn(t, x, y); if (a === null || b === null) { const da = cheb(x, y, sc[t][0], sc[t][1]), db = cheb(x, y, sc[1 - t][0], sc[1 - t][1]); return da / (da + db || 1); } return a / (a + b || 1); };
  const zoneOf = (t, x, y) => { const f = fOf(t, x, y); return f < 0.4 ? 'own' : f > 0.6 ? 'enemy' : 'mid'; };
  const onSpawn = (t, x, y) => cheb(x, y, sc[t][0], sc[t][1]) <= 2;
  // camp groups
  const tileG = new Map();
  for (const g of geo.groups) for (const c of g.camps) tileG.set(c[0] * 1000 + c[1], g.i);
  const groupAt = (x, y) => { if (tileG.has(x * 1000 + y)) return tileG.get(x * 1000 + y); let best = -1, bd = 3; for (const g of geo.groups) for (const c of g.camps) { const dd = cheb(x, y, c[0], c[1]); if (dd < bd) { bd = dd; best = g.i; } } return best; };
  const gcls = (gi) => { if (gi < 0) return '?'; const ts = new Set(geo.groups[gi].camps.map((c) => c[2])); return ts.has('monolith') ? 'mono' : ts.has('golem') ? 'golem' : ts.has('elk') ? 'elk' : ts.has('wolf') ? 'wolf' : ts.has('gem') ? 'gem' : 'gold'; };
  const campTiles = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
  // per-body action rounds
  const acted = new Map(); // i -> Set(r) of rounds with a non-move action
  const moved = new Map();
  const champHit = new Map(); // i -> Set(r) rounds hitting an enemy champion
  const campHit = new Map();
  const add = (m, i, r) => { if (!m.has(i)) m.set(i, new Set()); m.get(i).add(r); };
  for (const x of d.dmg) { const [q, r, a, v] = x; if (a >= 0 && teamOf(a) !== teamOf(v)) add(champHit, a, r); }
  for (const x of d.cdmg) add(campHit, x[2], x[1]);
  const recallStart = new Map(); // i -> [r...]
  for (const e of d.ev) {
    if (e.who === undefined) continue;
    if (e.k === 'Move') add(moved, e.who, e.r);
    else if (e.k !== 'Cancel channel' && e.k !== 'Death' && e.k !== 'CaptureGems' && e.k !== 'Banked' && e.k !== 'Recall') add(acted, e.who, e.r);
    if (e.k === 'Recall') { if (!recallStart.has(e.who)) recallStart.set(e.who, []); recallStart.get(e.who).push(e.r); }
  }
  const T = [S, O].map((t) => ({
    team: t, name: t === S ? me.name : op.name, draft: (t === S ? me : op).draftPicks,
    bank: {}, caps: 0, capGems: 0, capsAt: {}, capGemsAt: {}, capZone: { own: [0, 0], mid: [0, 0], enemy: [0, 0] }, capCls: {},
    deaths: [], kills: 0, bagLost: 0, bagStolen: 0, trib: [], locks: [], maxhp: {}, gold: {}, idle: 0, idleRuns: [], recallsDone: 0, recallStarts: 0,
    firstDeath: null, cluster: { r20_150: 0, r150_400: 0, r400_800: 0, n4_150_400: 0 }, raids: 0, raidGems: 0, raidsUndef: 0, raidGemsUndef: 0,
    perBody: {},
  }));
  const TT = (t) => (t === S ? T[0] : T[1]);
  for (const t of [S, O]) for (const b of bodies.filter((b) => b.team === t)) TT(t).perBody[b.index] = { ty: b.type, deaths: 0, d200: 0, d400: 0, firstDeath: null, capGems: 0, caps: 0, kills: 0, banked: 0, maxBag: 0, deadRounds: 0 };
  // banked + maxhp + gold at checkpoints
  for (const cp of CP) {
    const r = Math.min(cp, final); const e = RS.get(r); if (!e) continue;
    for (const t of [S, O]) {
      TT(t).bank[cp] = e[1 + t];
      let mh = 0, gd = 0; for (const c of e[3]) if (teamOf(c[0]) === t) { mh += c[4]; gd += c[7]; }
      TT(t).maxhp[cp] = mh; TT(t).gold[cp] = gd;
    }
  }
  // captures
  for (const e of d.ev) {
    if (e.k !== 'CaptureGems') continue;
    const t = teamOf(e.who); const X = TT(t);
    X.caps++; X.capGems += e.gems;
    for (const cp of CP) if (e.r <= cp) { X.capsAt[cp] = (X.capsAt[cp] || 0) + 1; X.capGemsAt[cp] = (X.capGemsAt[cp] || 0) + e.gems; }
    const z = zoneOf(t, e.at[0], e.at[1]); X.capZone[z][0]++; X.capZone[z][1] += e.gems;
    const cl = gcls(groupAt(e.at[0], e.at[1])); if (!X.capCls[cl]) X.capCls[cl] = [0, 0]; X.capCls[cl][0]++; X.capCls[cl][1] += e.gems;
    X.perBody[e.who].capGems += e.gems; X.perBody[e.who].caps++;
    // raid: capture in the other team's own zone
    if (zoneOf(1 - t, e.at[0], e.at[1]) === 'own') {
      X.raids++; X.raidGems += e.gems;
      let def = false; const m = PM.get(e.r) || PM.get(e.r - 1);
      if (m) for (const c of m.values()) if (teamOf(c[0]) === 1 - t && c[5] && cheb(c[1], c[2], e.at[0], e.at[1]) <= 8) def = true;
      if (!def) { X.raidsUndef++; X.raidGemsUndef += e.gems; }
    }
  }
  // banked per body
  for (const e of d.ev) if (e.k === 'Banked') TT(teamOf(e.who)).perBody[e.who].banked += e.gems;
  // deaths
  const stunsOn = new Map(); for (const s of d.stun) { if (!stunsOn.has(s[3])) stunsOn.set(s[3], []); stunsOn.get(s[3]).push(s); }
  for (const e of d.ev) {
    if (e.k !== 'Death') continue;
    const t = teamOf(e.who); const X = TT(t); const r = e.r;
    const at = e.at; const z = zoneOf(t, at[0], at[1]);
    const killerTy = typeof e.by === 'number' ? tyOf(e.by) : 'camp';
    const byChamp = typeof e.by === 'number' && teamOf(e.by) !== t;
    const prev = PM.get(r - 1) || new Map();
    let al = 0, en = 0, enHp = 0; const me1 = prev.get(e.who);
    for (const c of prev.values()) { if (!c[5] || c[0] === e.who) continue; const dd = cheb(c[1], c[2], at[0], at[1]); if (dd <= 6) { if (teamOf(c[0]) === t) al++; else { en++; enHp += c[4]; } } }
    const p10 = P(Math.max(1, r - 10), e.who); const p3 = P(Math.max(1, r - 3), e.who);
    const d10 = p10 && p10[5] ? dOwn(t, p10[1], p10[2]) : null, dNow = dOwn(t, at[0], at[1]);
    let hitsC = 0, hitsK = 0, movesN = 0; for (let k = r - 10; k < r; k++) { if (champHit.get(e.who)?.has(k)) hitsC++; if (campHit.get(e.who)?.has(k)) hitsK++; if (moved.get(e.who)?.has(k)) movesN++; }
    const dth = { r, ty: tyOf(e.who), z, bag: e.bag || 0, by: killerTy, byChamp, al6: al, en6: en, hp3: p3 && p3[5] ? +(p3[3] / p3[4]).toFixed(2) : null, mh: me1 ? me1[4] : null, enMh: en ? Math.round(enHp / en) : null, dOwn10: d10, dOwn: dNow, hitsC, hitsK, movesN, at };
    X.deaths.push(dth); X.bagLost += dth.bag;
    if (byChamp) { TT(1 - t).kills++; TT(1 - t).bagStolen += dth.bag; if (TT(1 - t).perBody[e.by]) TT(1 - t).perBody[e.by].kills++; }
    if (X.firstDeath === null) X.firstDeath = r;
    const pb = X.perBody[e.who]; pb.deaths++; if (r < 200) pb.d200++; if (r < 400) pb.d400++; if (pb.firstDeath === null) pb.firstDeath = r;
  }
  // dead rounds and max bag per body
  for (const [r, m] of PM) for (const c of m.values()) { const pb = TT(teamOf(c[0])).perBody[c[0]]; if (!c[5]) pb.deadRounds++; if (c[6] > pb.maxBag) pb.maxBag = c[6]; }
  // tribute episodes
  const evBy = new Map(); for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
  const locks = d.ev.filter((e) => e.k === 'Place altar lock');
  for (const e of d.ev) {
    if (e.k !== 'Submit gems') continue;
    const b = e.who, t = teamOf(b), r0 = e.r, q0 = e.q; const altar = e.to;
    const c0 = P(r0, b) || P(r0 - 1, b); const bag = c0 ? c0[6] : 0;
    const need = Math.max(1, Math.ceil(bag / 10));
    // find the end: next event of b after q0
    let res = 'open', rEnd = null;
    const list = evBy.get(b) || [];
    for (const x of list) {
      if (x.q <= q0) continue;
      if (x.k === 'Gems submitted' || x.k === 'Banked') { res = 'done'; rEnd = x.r; break; }
      if (x.k === 'Death') { res = 'death'; rEnd = x.r; break; }
      if (x.k === 'Cancel channel') { res = 'self'; rEnd = x.r; break; }
      if (x.k === 'Submit gems') { res = 'restart'; rEnd = x.r; break; }
      if (x.k === 'Move' || x.k === 'Attack' || x.k === 'Cast ability' || x.k === 'Recall' || x.k === 'Shop' || x.k === 'Place ward' || x.k === 'Place altar lock') { res = 'other'; rEnd = x.r; break; }
    }
    if (rEnd === null) rEnd = final;
    // stun / lock inside the window (q0 .. end)
    const qEnd = (list.find((x) => x.q > q0 && x.r === rEnd) || { q: 1e12 }).q;
    let stunned = false, stunBy = null; for (const s of stunsOn.get(b) || []) if (s[0] > q0 && s[0] <= qEnd) { stunned = true; stunBy = s[2] >= 0 ? tyOf(s[2]) : 'camp'; break; }
    let locked = false; for (const L of locks) if (L.q > q0 && L.q <= qEnd && teamOf(L.who) !== t && cheb(L.to[0], L.to[1], altar[0], altar[1]) <= 0) { locked = true; break; }
    if (res !== 'done' && res !== 'death') { if (locked) res = 'lock'; else if (stunned) res = 'stun'; }
    // enemies near during the channel
    let enMax = 0, enRounds = 0, enStunMax = 0, firstEn = null, dmgIn = 0;
    for (let r = r0; r <= rEnd; r++) {
      const m = PM.get(r); if (!m) continue; const me2 = m.get(b); if (!me2) continue;
      let n = 0, ns = 0; for (const c of m.values()) if (teamOf(c[0]) !== t && c[5]) { const dd = cheb(c[1], c[2], me2[1], me2[2]); if (dd <= 5) { n++; if (STUNNERS.has(tyOf(c[0]))) ns++; } }
      if (n) { enRounds++; if (firstEn === null) firstEn = r - r0; }
      enMax = Math.max(enMax, n); enStunMax = Math.max(enStunMax, ns);
    }
    for (const x of d.dmg) if (x[3] === b && x[0] > q0 && x[0] <= qEnd) dmgIn += x[4];
    TT(t).trib.push({ r: r0, ty: tyOf(b), b, bag, need, res, len: rEnd - r0, stunBy, enMax, enRounds, enStunMax, firstEn, dmgIn, altar, z: zoneOf(t, altar[0], altar[1]) });
  }
  // locks: did they cancel an active enemy tribute?
  for (const L of locks) {
    const t = teamOf(L.who);
    const act = TT(1 - t).trib.find((x) => x.r <= L.r && x.r + x.len >= L.r && x.res === 'lock' && cheb(x.altar[0], x.altar[1], L.to[0], L.to[1]) === 0);
    TT(t).locks.push({ r: L.r, at: L.to, ty: tyOf(L.who), cancelled: act ? act.bag : 0 });
  }
  // idle runs: alive, off spawn, did not move and did not act, not channelling (tribute / completed recall), rounds >= 2
  const chan = new Map(); // i -> Set(r) channel rounds (tribute windows, the 6 rounds before a completed recall)
  for (const t of [S, O]) for (const x of TT(t).trib) for (let r = x.r; r <= x.r + x.len; r++) add(chan, x.b, r);
  for (const b of bodies) {
    let last = null;
    for (let r = 1; r <= final; r++) { const c = P(r, b.index); if (c && last && c[5] && last[5] && onSpawn(b.team, c[1], c[2]) && cheb(c[1], c[2], last[1], last[2]) >= 3) for (let k = r - 6; k <= r; k++) add(chan, b.index, k); if (c) last = c; }
  }
  for (const b of bodies) {
    const t = b.team; const X = TT(t); let run = 0, start = 0, at = null;
    const rs = [...PM.keys()].sort((a, c) => a - c);
    let last = null;
    for (const r of rs) {
      const c = PM.get(r).get(b.index);
      const still = c && c[5] && last && last[5] && c[1] === last[1] && c[2] === last[2] && !onSpawn(t, c[1], c[2]) && !moved.get(b.index)?.has(r) && !acted.get(b.index)?.has(r) && !chan.get(b.index)?.has(r);
      if (still) { if (!run) { start = r; at = [c[1], c[2]]; } run++; }
      else if (run) {
        X.idle += run;
        if (run >= 25) X.idleRuns.push({ ty: b.type, r: start, len: run, at, camp: campTiles.has(at[0] * 1000 + at[1]) ? 1 : 0, z: zoneOf(t, at[0], at[1]) });
        run = 0;
      }
      last = c;
    }
    if (run) { X.idle += run; if (run >= 25) X.idleRuns.push({ ty: b.type, r: start, len: run, at, camp: campTiles.has(at[0] * 1000 + at[1]) ? 1 : 0, z: zoneOf(t, at[0], at[1]), open: 1 }); }
  }
  // completed recalls: alive in consecutive rounds, jump >= 3 tiles onto own spawn
  for (const b of bodies) {
    const t = b.team; let last = null;
    for (let r = 1; r <= final; r++) { const c = P(r, b.index); if (c && last && c[5] && last[5] && onSpawn(t, c[1], c[2]) && cheb(c[1], c[2], last[1], last[2]) >= 3) TT(t).recallsDone++; if (c) last = c; }
    TT(t).recallStarts += (recallStart.get(b.index) || []).length;
  }
  // cohesion: largest connected cluster (Chebyshev <= 4) of living bodies, mean over windows
  const win = [[20, 150, 'r20_150'], [150, 400, 'r150_400'], [400, 800, 'r400_800']];
  for (const t of [S, O]) {
    for (const [a, b2, k] of win) {
      let s = 0, n = 0, n4 = 0;
      for (let r = a; r < Math.min(b2, final); r++) {
        const m = PM.get(r); if (!m) continue; const L = [...m.values()].filter((c) => teamOf(c[0]) === t && c[5]);
        if (!L.length) continue;
        const seen = new Array(L.length).fill(false); let best = 0;
        for (let i = 0; i < L.length; i++) { if (seen[i]) continue; let sz = 0; const st = [i]; seen[i] = true; while (st.length) { const u = st.pop(); sz++; for (let j = 0; j < L.length; j++) if (!seen[j] && cheb(L[u][1], L[u][2], L[j][1], L[j][2]) <= 4) { seen[j] = true; st.push(j); } } best = Math.max(best, sz); }
        s += best; n++; if (best >= 4) n4++;
      }
      TT(t).cluster[k] = n ? +(s / n).toFixed(2) : null;
      if (k === 'r150_400') TT(t).cluster.n4_150_400 = n ? +(n4 / n).toFixed(2) : null;
    }
  }
  const out = {
    file: base, key, map, S, win: me.result === 'win' ? 1 : 0, outcomeCheck: d.meta.outcome === (S === 0 ? 1 : 2) ? 1 : 0, opp: op.name, side: me.side, final,
    sub: [d.meta.submitted[S], d.meta.submitted[O]], at: row.createdAt, T,
  };
  console.log(JSON.stringify(out));
}
