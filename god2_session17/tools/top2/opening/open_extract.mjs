#!/usr/bin/env node
// Opening (rounds 1..RMAX, default 300) per team from tools/live/fightdump.mjs dumps + map geometry (strat_mapgeo output with BFS
// walking distances): per body first move / first camp hit (group, zone, walk distance, distance rank) / capture / bank / mid entry
// / first arrival home; per team captures, banks, gold, max HP at checkpoints, cohesion, mid presence, squads; per game engagements
// (first fight) / first kill, post-capture decisions (bag, altar walking distance, next: bank / cap / home / death), bank trips.
//   node tools/top2/opening/open_extract.mjs GEO.jsonl RMAX dump.json.gz...  > out.jsonl   (one JSON line per dump)
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const GEMS = { wolf: 4, elk: 15, gem: 7, gold: 0, monolith: 200, golem: 36 };
const GOLD = { wolf: 40, elk: 90, gem: 0, gold: 20, monolith: 300, golem: 160 };
const HP = { wolf: 1350, elk: 2400, gem: 120, gold: 120, monolith: 20000, golem: 5000 };
const TYPES = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem'];
const CPS = [50, 100, 150, 200, 250, 300];
const WINS = [[1, 50], [51, 100], [101, 150], [151, 200], [201, 300]];
const LINK = 5; // cohesion: bodies within Chebyshev 5 are linked
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

const [geoFile, rmaxArg, ...files] = process.argv.slice(2);
const RMAX = +rmaxArg || 300;
const geo = new Map();
for (const l of fs.readFileSync(geoFile, 'utf8').split('\n')) if (l.trim()) { const g = JSON.parse(l); geo.set(g.map, g); }

function bfs(W, H, grid, starts) {
  const d = new Int32Array(W * H).fill(-1);
  const q = [];
  for (const [x, y] of starts) { d[y * W + x] = 0; q.push(y * W + x); }
  for (let h = 0; h < q.length; ++h) {
    const p = q[h], x = p % W, y = (p - x) / W;
    for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) {
      if (!dx && !dy) continue;
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const c = grid[ny][nx];
      if (c === '#' || c === 'o' || c === 'A') continue;
      const np = ny * W + nx;
      if (d[np] >= 0) continue;
      d[np] = d[p] + 1; q.push(np);
    }
  }
  return d;
}

for (const file of files) {
  let d;
  try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); continue; }
  const base = path.basename(file).replace(/\.json\.gz$/, '');
  const m = base.match(/^(.*)_([0-9a-f]{8})$/);
  const map = m ? m[1] : base, mid8 = m ? m[2] : '';
  const g0 = geo.get(map);
  const meta = d.meta;
  const W = meta.width, H = meta.height;
  const bodies = meta.bodies;
  const teamOf = new Map(bodies.map((b) => [b.index, b.team]));
  const typeOf = new Map(bodies.map((b) => [b.index, b.type]));
  // rounds: last row per round number wins (the first row is a pre-game snapshot)
  const S = [];
  for (const row of d.R) S[row[0]] = row;
  const final = meta.finalRound;
  const startRow = d.R[0];
  const startPos = new Map(startRow[3].map((c) => [c[0], [c[1], c[2]]]));
  const pos = (r, b) => { const row = S[Math.min(r, final)]; if (!row) return null; const c = row[3].find((c) => c[0] === b); return c ? c : null; };
  // which mapgeo spawn is team 0's
  let flip = false;
  if (g0) {
    const t0 = bodies.filter((b) => b.team === 0).map((b) => startPos.get(b.index));
    const onA = t0.filter((p) => g0.spawnA.some((s) => s[0] === p[0] && s[1] === p[1])).length;
    const onB = t0.filter((p) => g0.spawnB.some((s) => s[0] === p[0] && s[1] === p[1])).length;
    flip = onB > onA;
  }
  const dist = g0 ? (flip ? [g0.dB, g0.dA] : [g0.dA, g0.dB]) : null; // dist[t] = walking distance from team t's spawn
  const spawnTiles = g0 ? (flip ? [g0.spawnB, g0.spawnA] : [g0.spawnA, g0.spawnB]) : [[], []];
  const spawnSet = spawnTiles.map((ts) => new Set(ts.map((s) => s[0] * 1000 + s[1])));
  const tileD = (t, x, y) => {
    if (!dist) return -1;
    const v = dist[t][y * W + x];
    if (v >= 0) return v;
    let best = -1; // camp / blocked tile: nearest walkable neighbour + 1
    for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) {
      const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const w = dist[t][ny * W + nx]; if (w >= 0 && (best < 0 || w + 1 < best)) best = w + 1;
    }
    return best;
  };
  const fOf = (t, x, y) => {
    if (spawnSet[t].has(x * 1000 + y)) return 0;
    const a = tileD(t, x, y), b = tileD(1 - t, x, y);
    if (a < 0 && b < 0) return null; if (b < 0) return 0; if (a < 0) return 1;
    return a + b > 0 ? a / (a + b) : 0.5;
  };
  const zoneOf = (f) => (f === null ? '?' : f < 0.4 ? 'O' : f <= 0.6 ? 'M' : 'T');
  // altars (walking distance from any tile computed on demand)
  const altars = g0 ? g0.altars.map((a) => [a[0], a[1]]) : [];
  let altarDist = null;
  if (g0 && altars.length) {
    // BFS from all altar-adjacent walkable tiles (tribute range = Chebyshev 1)
    const st = [];
    for (const [ax, ay] of altars) for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) {
      const nx = ax + dx, ny = ay + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const c = g0.grid[ny][nx]; if (c === '#' || c === 'o' || c === 'A') continue; st.push([nx, ny]);
    }
    altarDist = bfs(W, H, g0.grid, st);
  }
  const altarD = (x, y) => { if (!altarDist) return -1; const v = altarDist[y * W + x]; if (v >= 0) return v; let b = -1; for (let dx = -1; dx <= 1; ++dx) for (let dy = -1; dy <= 1; ++dy) { const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue; const w = altarDist[ny * W + nx]; if (w >= 0 && (b < 0 || w + 1 < b)) b = w + 1; } return b; };
  // camp groups
  const camps = meta.camps.map((c) => ({ ...c, type: typeof c.type === 'number' ? (TYPES[c.type] || String(c.type)) : c.type }));
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = new Map(camps.map((c) => [c.index, c.index]));
  const find = (i) => { while (par.get(i) !== i) { par.set(i, par.get(par.get(i))); i = par.get(i); } return i; };
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1], [-1, 0], [0, -1]]) {
    const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) { const a = find(c.index), b = find(j); if (a !== b) par.set(a, b); }
  }
  const groups = new Map();
  for (const c of camps) {
    const g = find(c.index);
    if (!groups.has(g)) groups.set(g, { id: g, camps: [], mix: {}, gems: 0, gold: 0, hp: 0 });
    const G = groups.get(g); G.camps.push(c); G.mix[c.type] = (G.mix[c.type] || 0) + 1;
    G.gems += GEMS[c.type] || 0; G.gold += GOLD[c.type] || 0; G.hp += HP[c.type] || c.hp || 0;
  }
  const campGroup = new Map(camps.map((c) => [c.index, find(c.index)]));
  for (const G of groups.values()) {
    G.d = [0, 1].map((t) => { let b = -1; for (const c of G.camps) { const v = tileD(t, c.x, c.y); if (v >= 0 && (b < 0 || v < b)) b = v; } return b; });
    G.f = [0, 1].map((t) => (G.d[t] >= 0 && G.d[1 - t] >= 0 && G.d[0] + G.d[1] > 0 ? G.d[t] / (G.d[0] + G.d[1]) : null));
    G.zone = [0, 1].map((t) => zoneOf(G.f[t]));
    G.cls = G.mix.monolith ? 'mono' : G.mix.golem ? 'golem' : G.mix.elk ? 'elk' : G.mix.wolf ? 'wolf' : G.gems > 0 ? 'gem' : 'gold';
    G.ad = Math.min(...G.camps.map((c) => { const v = altarD(c.x, c.y); return v < 0 ? 1e9 : v; }));
  }
  // rank of groups by walking distance per team (only groups with gems > 0 or gold > 0)
  const rankOf = [0, 1].map((t) => {
    const arr = [...groups.values()].filter((G) => G.d[t] >= 0).sort((a, b) => a.d[t] - b.d[t]);
    return new Map(arr.map((G, i) => [G.id, i + 1]));
  });
  const valRank = [0, 1].map((t) => { // value per distance (gems + gold/10) / (d + 10)
    const arr = [...groups.values()].filter((G) => G.d[t] >= 0).sort((a, b) => (b.gems + b.gold / 10) / (b.d[t] + 10) - (a.gems + a.gold / 10) / (a.d[t] + 10));
    return new Map(arr.map((G, i) => [G.id, i + 1]));
  });
  const ev = d.ev;
  const capt = ev.filter((e) => e.k === 'CaptureGems');
  const banks = ev.filter((e) => e.k === 'Banked');
  const deaths = ev.filter((e) => e.k === 'Death');
  const shops = ev.filter((e) => e.k === 'Shop');
  const recalls = ev.filter((e) => e.k === 'Recall');
  const locks = ev.filter((e) => e.k === 'Place altar lock');
  const cancels = ev.filter((e) => e.k === 'Cancel channel');
  const cc = d.dmg.filter((x) => x[2] >= 0 && x[3] >= 0 && x[2] !== x[3] && teamOf.get(x[2]) !== teamOf.get(x[3]));
  const out = { file: base, map, mid8, W, H, final, outcome: meta.outcome, submitted: meta.submitted, flip, geo: !!g0,
    feat: g0 ? g0.feat : null, teams: [] };
  // arrivals home (completed recalls; Recall events alone are noisy: some bots start and cancel a recall every turn):
  // alive at r-1 more than 2 tiles from its own spawn tiles, alive on a spawn tile at r
  const homeArr = [[], []];
  const homeBody = new Map(bodies.map((b) => [b.index, []]));
  for (let r = 2; r <= Math.min(RMAX, final); ++r) {
    const a = S[r - 1], b = S[r]; if (!a || !b) continue;
    for (const c of b[3]) {
      const t = teamOf.get(c[0]); if (!c[5] || !spawnSet[t].has(c[1] * 1000 + c[2])) continue;
      const p = a[3].find((x) => x[0] === c[0]); if (!p || !p[5]) continue;
      let dmin = 1e9; for (const s of spawnTiles[t]) dmin = Math.min(dmin, cheb([p[1], p[2]], s));
      if (dmin > 2) { homeArr[t].push(r); homeBody.get(c[0]).push(r); }
    }
  }
  // after each capture (r <= RMAX): the body's bag, walking distance from the capture tile to the nearest altar, and what came next
  out.decisions = capt.filter((e) => e.r <= RMAX).map((e) => {
    const b = e.who, t = e.team;
    const row = S[e.r]; const c = row ? row[3].find((x) => x[0] === b) : null; const bag = c ? c[6] : e.gems;
    const nb = banks.find((q) => q.who === b && q.r >= e.r);
    const nc = capt.find((q) => q.who === b && q.r > e.r);
    const nd = deaths.find((q) => q.who === b && q.r >= e.r);
    const nh = homeBody.get(b).find((h) => h >= e.r); // same round = recall channelled during the capture timer
    const opts = [['bank', nb?.r], ['cap', nc?.r], ['death', nd?.r], ['home', nh]].filter((o) => o[1] !== undefined).sort((x, y) => x[1] - y[1]);
    const next = opts.length ? opts[0] : ['none', null];
    return { r: e.r, t, b, type: typeOf.get(b), bag, gems: e.gems, ad: altarD(e.at[0], e.at[1]), next: next[0], dr: next[1] !== null ? next[1] - e.r : null,
      zone: (() => { const ci = at.get(e.at[0] * 1000 + e.at[1]); const G = ci === undefined ? null : groups.get(campGroup.get(ci)); return G ? G.zone[t] : zoneOf(fOf(t, e.at[0], e.at[1])); })() };
  });
  out.bankTrips = banks.filter((q) => q.r <= RMAX).map((q) => {
    const pc = [...capt].reverse().find((e) => e.who === q.who && e.r <= q.r);
    return { r: q.r, t: q.team, b: q.who, gems: q.gems, fromCapR: pc ? q.r - pc.r : null, capAd: pc ? altarD(pc.at[0], pc.at[1]) : null,
      viaHome: pc ? homeBody.get(q.who).some((h) => h >= pc.r && h <= q.r) : null };
  });

  // capture records per team (merge split rewards: same group, same round)
  const capRec = [[], []];
  for (const e of capt) {
    if (e.r > RMAX) continue;
    const t = e.team; const ci = at.get(e.at[0] * 1000 + e.at[1]); const g = ci === undefined ? -1 : campGroup.get(ci);
    let rec = capRec[t].find((c) => c.g === g && c.r === e.r);
    if (!rec) {
      const G = groups.get(g);
      const from = e.r - 60;
      const hit = d.cdmg.filter((x) => x[1] > from && x[1] <= e.r && campGroup.get(x[3]) === g);
      const mine = new Set(hit.filter((x) => teamOf.get(x[2]) === t).map((x) => x[2]));
      const theirs = new Set(hit.filter((x) => teamOf.get(x[2]) !== t).map((x) => x[2]));
      const firstMine = hit.filter((x) => teamOf.get(x[2]) === t).reduce((a, x) => Math.min(a, x[1]), 1e9);
      const firstTheirs = hit.filter((x) => teamOf.get(x[2]) !== t).reduce((a, x) => Math.min(a, x[1]), 1e9);
      rec = { r: e.r, g, gems: 0, gold: 0, split: 0, zone: G ? G.zone[t] : '?', f: G ? G.f[t] : null, cls: G ? G.cls : '?', d: G ? G.d[t] : -1,
        hitters: mine.size, enemyHitters: theirs.size, killRounds: firstMine < 1e9 ? e.r - firstMine : null, contested: firstTheirs < firstMine,
        ad: G ? G.ad : -1, at: e.at };
      capRec[t].push(rec);
    }
    rec.gems += e.gems; rec.gold += e.gold; rec.split++;
  }
  // per body tracks
  const bodyOut = [];
  for (const b of bodies) {
    const t = b.team, i = b.index;
    const o = { i, t, type: b.type, firstMove: null, firstHit: null, firstCap: null, firstBank: null, firstMid: null, firstDeath: null,
      firstShop: null, firstRecall: null, groupsHit100: 0, groupsHit300: 0, seq: [] };
    const sp = startPos.get(i);
    for (let r = 1; r <= Math.min(RMAX, final); ++r) {
      const c = pos(r, i); if (!c) continue;
      if (o.firstMove === null && (c[1] !== sp[0] || c[2] !== sp[1])) o.firstMove = r;
      if (o.firstMid === null && c[5]) { const f = fOf(t, c[1], c[2]); if (f !== null && f >= 0.4 && f <= 0.6) o.firstMid = r; }
    }
    const hits = d.cdmg.filter((x) => x[2] === i && x[1] <= RMAX);
    if (hits.length) {
      const h = hits[0], g = campGroup.get(h[3]), G = groups.get(g), cmp = camps.find((c) => c.index === h[3]);
      o.firstHit = { r: h[1], g, cls: G.cls, type: cmp.type, zone: G.zone[t], f: G.f[t], d: G.d[t], cheb: cheb(sp, [cmp.x, cmp.y]), rank: rankOf[t].get(g) ?? null,
        vrank: valRank[t].get(g) ?? null, gems: G.gems, gold: G.gold, hp: G.hp };
    }
    const seen = new Set(), seen100 = new Set();
    for (const h of hits) { const g = campGroup.get(h[3]); if (!seen.has(g)) { seen.add(g); o.seq.push([h[1], g]); } if (h[1] <= 100) seen100.add(g); }
    o.groupsHit100 = seen100.size; o.groupsHit300 = seen.size;
    const fc = capt.find((e) => e.who === i && e.r <= RMAX);
    if (fc) { const ci = at.get(fc.at[0] * 1000 + fc.at[1]); const G = groups.get(campGroup.get(ci)); o.firstCap = { r: fc.r, gems: fc.gems, gold: fc.gold, zone: G ? G.zone[t] : '?', cls: G ? G.cls : '?' }; }
    const fb = banks.find((e) => e.who === i && e.r <= RMAX);
    if (fb) o.firstBank = { r: fb.r, gems: fb.gems };
    const fd = deaths.find((e) => e.who === i && e.r <= RMAX);
    if (fd) o.firstDeath = { r: fd.r, by: typeof fd.by === 'number' ? 'champ' : 'camp', bag: fd.bag, zone: zoneOf(fOf(t, fd.at[0], fd.at[1])) };
    const fs_ = shops.find((e) => e.who === i && e.r <= RMAX); if (fs_) o.firstShop = fs_.r;
    o.firstRecall = homeBody.get(i)[0] ?? null; // first arrival home while alive
    bodyOut.push(o);
  }
  // team level
  for (const t of [0, 1]) {
    const mine = bodies.filter((b) => b.team === t).map((b) => b.index);
    const T = { t, n: mine.length, types: mine.map((i) => typeOf.get(i)), cp: {}, win: {}, caps: capRec[t],
      hp0: startRow[3].filter((c) => teamOf.get(c[0]) === t).reduce((a, c) => a + c[4], 0) };
    const bo = bodyOut.filter((o) => o.t === t);
    T.bodies = bo;
    // squads: bodies grouped by first-hit group
    const sq = new Map();
    for (const o of bo) if (o.firstHit) sq.set(o.firstHit.g, (sq.get(o.firstHit.g) || 0) + 1);
    T.squads = [...sq.values()].sort((a, b) => b - a);
    const hitBodies = bo.filter((o) => o.firstHit);
    T.firstHit = hitBodies.length ? Math.min(...hitBodies.map((o) => o.firstHit.r)) : null;
    // checkpoints
    // gold earned: per body and round max(positive gold delta, event income of that round). Event income = capture gold (exact) +
    // 100 per kill + Marcella's 2 gold per banked gem; it matters when a body earns and spends in the same round (capture completes,
    // a recall channelled during the capture timer lands it on spawn, it shops at once).
    const goldEarned = new Map(mine.map((i) => [i, 0]));
    const evInc = new Map();
    const addInc = (b, r, g) => { const k = b * 10000 + r; evInc.set(k, (evInc.get(k) || 0) + g); };
    for (const e of capt) if (teamOf.get(e.who) === t) addInc(e.who, e.r, e.gold);
    for (const e of deaths) if (typeof e.by === 'number' && teamOf.get(e.by) === t && e.team !== t) addInc(e.by, e.r, 100);
    for (const e of banks) if (teamOf.get(e.who) === t && typeOf.get(e.who) === 'Marcella') addInc(e.who, e.r, 2 * e.gems);
    let lastRow = null;
    const cpOut = {};
    for (let r = 1; r <= Math.min(RMAX, final); ++r) {
      const row = S[r]; if (!row) continue;
      if (lastRow) for (const c of row[3]) {
        if (teamOf.get(c[0]) !== t) continue; const p = lastRow[3].find((x) => x[0] === c[0]);
        const dlt = p ? Math.max(0, c[7] - p[7]) : 0;
        goldEarned.set(c[0], goldEarned.get(c[0]) + Math.max(dlt, evInc.get(c[0] * 10000 + r) || 0));
      }
      lastRow = row;
      if (CPS.includes(r)) {
        const cs = row[3].filter((c) => teamOf.get(c[0]) === t);
        cpOut[r] = {
          banked: row[1 + t], carried: cs.reduce((a, c) => a + c[6], 0), gold: [...goldEarned.values()].reduce((a, v) => a + v, 0),
          held: cs.reduce((a, c) => a + c[7], 0), maxHp: cs.reduce((a, c) => a + c[4], 0), alive: cs.reduce((a, c) => a + c[5], 0),
          caps: capRec[t].filter((c) => c.r <= r).length, capGems: capRec[t].filter((c) => c.r <= r).reduce((a, c) => a + c.gems, 0),
          capGold: capRec[t].filter((c) => c.r <= r).reduce((a, c) => a + c.gold, 0),
          midGems: capRec[t].filter((c) => c.r <= r && c.zone === 'M').reduce((a, c) => a + c.gems, 0),
          ownGems: capRec[t].filter((c) => c.r <= r && c.zone === 'O').reduce((a, c) => a + c.gems, 0),
          enemyGems: capRec[t].filter((c) => c.r <= r && c.zone === 'T').reduce((a, c) => a + c.gems, 0),
          kills: deaths.filter((e) => e.r <= r && e.team !== t && typeof e.by === 'number' && teamOf.get(e.by) === t).length,
          deaths: deaths.filter((e) => e.r <= r && e.team === t).length,
          deathsChamp: deaths.filter((e) => e.r <= r && e.team === t && typeof e.by === 'number').length,
          bagLost: deaths.filter((e) => e.r <= r && e.team === t).reduce((a, e) => a + (e.bag || 0), 0),
          banks: banks.filter((e) => e.r <= r && e.team === t).length,
          homes: homeArr[t].filter((h) => h <= r).length,
          locks: locks.filter((e) => e.r <= r && teamOf.get(e.who) === t).length,
          // captures whose capturer lands home in the same or the next round (recall channelled during the capture timer)
          capRecall: capt.filter((e) => e.r <= r && e.team === t && homeBody.get(e.who).some((h) => h >= e.r && h <= e.r + 1)).length,
          recallStarts: recalls.filter((e) => e.r <= r && teamOf.get(e.who) === t).length,
          cancels: cancels.filter((e) => e.r <= r && teamOf.get(e.who) === t).length,
        };
      }
    }
    T.cp = cpOut;
    // windows: cohesion, dispersion, mid presence, distinct groups worked
    for (const [a, b] of WINS) {
      let n = 0, lc = 0, lcf = 0, disp = 0, midN = 0, ownN = 0, enN = 0, alive = 0, pairs = 0, pairD = 0, offSpawn = 0;
      for (let r = a; r <= Math.min(b, final); ++r) {
        const row = S[r]; if (!row) continue;
        const cs = row[3].filter((c) => teamOf.get(c[0]) === t && c[5]);
        if (!cs.length) continue;
        n++; alive += cs.length;
        // largest cluster
        const k = cs.length, seenC = new Array(k).fill(false); let best = 0;
        for (let s = 0; s < k; ++s) {
          if (seenC[s]) continue; let size = 0; const st = [s]; seenC[s] = true;
          while (st.length) { const u = st.pop(); size++; for (let v = 0; v < k; ++v) if (!seenC[v] && cheb([cs[u][1], cs[u][2]], [cs[v][1], cs[v][2]]) <= LINK) { seenC[v] = true; st.push(v); } }
          best = Math.max(best, size);
        }
        lc += best; lcf += best / k;
        const mx = cs.reduce((s, c) => s + c[1], 0) / k, my = cs.reduce((s, c) => s + c[2], 0) / k;
        disp += cs.reduce((s, c) => s + Math.max(Math.abs(c[1] - mx), Math.abs(c[2] - my)), 0) / k;
        for (let u = 0; u < k; ++u) for (let v = u + 1; v < k; ++v) { pairs++; pairD += cheb([cs[u][1], cs[u][2]], [cs[v][1], cs[v][2]]); }
        for (const c of cs) {
          const f = fOf(t, c[1], c[2]); const z = zoneOf(f);
          if (z === 'M') midN++; else if (z === 'T') enN++; else ownN++;
          if (!spawnSet[t].has(c[1] * 1000 + c[2])) offSpawn++;
        }
      }
      // distinct groups hit per 10-round slice (how many work sites at once)
      let slices = 0, sites = 0;
      for (let r0 = a; r0 <= Math.min(b, final); r0 += 10) {
        const gs = new Set(d.cdmg.filter((x) => x[1] >= r0 && x[1] < r0 + 10 && teamOf.get(x[2]) === t).map((x) => campGroup.get(x[3])));
        slices++; sites += gs.size;
      }
      T.win[`${a}-${b}`] = n ? { lc: lc / n, lcf: lcf / n, disp: disp / n, pairD: pairs ? pairD / pairs : 0, mid: midN / n, own: ownN / n, enemy: enN / n,
        alive: alive / n, offSpawn: offSpawn / n, sites: slices ? sites / slices : 0 } : null;
    }
    // time series every 10 rounds: [r, alive, in mid band, in enemy zone, largest-cluster share, gold earned (from cpOut-like
    // accumulation), captured gems, mid gems, banked, kills, deaths, max-HP bought]; first round with >= 2 / >= 3 bodies in the mid band
    {
      const ge = new Map(mine.map((i) => [i, 0])); let lr = null; T.ts = []; T.firstMid2 = null; T.firstMid3 = null;
      for (let r = 1; r <= Math.min(RMAX, final); ++r) {
        const row = S[r]; if (!row) continue;
        if (lr) for (const c of row[3]) {
          if (teamOf.get(c[0]) !== t) continue; const p = lr[3].find((x) => x[0] === c[0]);
          ge.set(c[0], ge.get(c[0]) + Math.max(p ? Math.max(0, c[7] - p[7]) : 0, evInc.get(c[0] * 10000 + r) || 0));
        }
        lr = row;
        const cs = row[3].filter((c) => teamOf.get(c[0]) === t && c[5]);
        let mid = 0, en = 0;
        for (const c of cs) { const z = zoneOf(fOf(t, c[1], c[2])); if (z === 'M') mid++; else if (z === 'T') en++; }
        if (T.firstMid2 === null && mid >= 2) T.firstMid2 = r;
        if (T.firstMid3 === null && mid >= 3) T.firstMid3 = r;
        if (r % 10) continue;
        const k = cs.length, seenC = new Array(k).fill(false); let best = 0;
        for (let s = 0; s < k; ++s) {
          if (seenC[s]) continue; let size = 0; const st = [s]; seenC[s] = true;
          while (st.length) { const u = st.pop(); size++; for (let v = 0; v < k; ++v) if (!seenC[v] && cheb([cs[u][1], cs[u][2]], [cs[v][1], cs[v][2]]) <= LINK) { seenC[v] = true; st.push(v); } }
          best = Math.max(best, size);
        }
        const all = row[3].filter((c) => teamOf.get(c[0]) === t);
        T.ts.push([r, k, mid, en, k ? +(best / k).toFixed(3) : 0, [...ge.values()].reduce((a, v) => a + v, 0),
          capRec[t].filter((c) => c.r <= r).reduce((a, c) => a + c.gems, 0), capRec[t].filter((c) => c.r <= r && c.zone === 'M').reduce((a, c) => a + c.gems, 0),
          row[1 + t], deaths.filter((e) => e.r <= r && e.team !== t && typeof e.by === 'number' && teamOf.get(e.by) === t).length,
          deaths.filter((e) => e.r <= r && e.team === t).length, all.reduce((a, c) => a + c[4], 0) - T.hp0]);
      }
    }
    // first capture / bank / mid
    T.firstCap = capRec[t].length ? capRec[t][0] : null;
    const fbk = banks.filter((e) => e.team === t && e.r <= RMAX);
    T.firstBank = fbk.length ? { r: fbk[0].r, gems: fbk.filter((e) => e.r === fbk[0].r).reduce((a, e) => a + e.gems, 0), ad: altarD(fbk[0].at[0], fbk[0].at[1]) } : null;
    T.bankList = fbk.map((e) => [e.r, e.who, e.gems]);
    const mids = bo.map((o) => o.firstMid).filter((v) => v !== null);
    T.firstMid = mids.length ? Math.min(...mids) : null;
    T.midBodies = mids.length;
    const midCap = capRec[t].find((c) => c.zone === 'M');
    T.firstMidCap = midCap ? midCap.r : null;
    out.teams.push(T);
  }
  // first champion-vs-champion damage and its engagement
  const vpos = (r, v) => { const c = pos(r, v); return c && c[5] && c[1] >= 0 ? [c[1], c[2]] : null; };
  const eng = [];
  for (const x of cc) {
    const p = vpos(x[1] - 1, x[3]) || vpos(x[1], x[3]) || vpos(x[1] - 1, x[2]) || vpos(x[1], x[2]);
    const last = eng[eng.length - 1];
    if (last && x[1] - last.rEnd <= 6 && (!p || !last.lp || cheb(p, last.lp) <= 10)) { last.ev.push(x); last.rEnd = x[1]; if (p) last.lp = p; }
    else eng.push({ r0: x[1], rEnd: x[1], ev: [x], lp: p, p0: p });
  }
  // every champion kill belongs to the first engagement that covers its round and contains the killer
  const killDeaths = deaths.filter((q) => typeof q.by === 'number' && teamOf.get(q.by) !== q.team);
  const owner = new Map();
  for (const q of killDeaths) {
    const e = eng.find((e) => q.r >= e.r0 && q.r <= e.rEnd + 1 && e.ev.some((x) => x[2] === q.by || x[3] === q.who));
    if (e) owner.set(q, e);
  }
  const engOut = eng.filter((e) => e.r0 <= RMAX).map((e) => {
    const striker = teamOf.get(e.ev[0][2]);
    const dmg = [0, 0], dmg3 = [0, 0], part = [new Set(), new Set()];
    for (const x of e.ev) { const ta = teamOf.get(x[2]); dmg[ta] += x[4]; if (x[1] <= e.r0 + 2) dmg3[ta] += x[4]; part[ta].add(x[2]); part[1 - ta].add(x[3]); }
    const dd = killDeaths.filter((q) => owner.get(q) === e);
    const dead = [0, 0]; for (const q of dd) dead[q.team]++;
    // local numbers at the first strike: bodies of each team within 8 of the first victim
    const near = [0, 0], nearHp = [0, 0];
    const row = S[Math.max(1, e.r0 - 1)];
    if (row && e.p0) for (const c of row[3]) if (c[5] && cheb([c[1], c[2]], e.p0) <= 8) { near[teamOf.get(c[0])]++; nearHp[teamOf.get(c[0])] += c[3]; }
    const z = e.p0 ? zoneOf(fOf(striker, e.p0[0], e.p0[1])) : '?';
    const firstDeathTeam = dd.length ? dd[0].team : null;
    return { r0: e.r0, rEnd: e.rEnd, striker, strikerType: typeOf.get(e.ev[0][2]), victimType: typeOf.get(e.ev[0][3]), zoneForStriker: z,
      at: e.p0, dmg, dmg3, part: part.map((s) => s.size), dead, firstDeathTeam, near, nearHp, hits: e.ev.length };
  });
  out.eng = engOut;
  const fk = deaths.find((q) => typeof q.by === 'number' && teamOf.get(q.by) !== q.team);
  out.firstKill = fk ? { r: fk.r, killerTeam: teamOf.get(fk.by), victimType: typeOf.get(fk.who), killerType: typeOf.get(fk.by), bag: fk.bag,
    zoneForKiller: zoneOf(fOf(teamOf.get(fk.by), fk.at[0], fk.at[1])) } : null;
  // group table (static map value relative to each team)
  out.groups = [...groups.values()].map((G) => ({ id: G.id, cls: G.cls, gems: G.gems, gold: G.gold, hp: G.hp, d: G.d, f: G.f, zone: G.zone, ad: G.ad, n: G.camps.length }));
  console.log(JSON.stringify(out));
}
