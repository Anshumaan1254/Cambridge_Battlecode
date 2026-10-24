#!/usr/bin/env node
// Strategy features of one replay (an_strategy): banked curves, captures by zone / camp class / bodies present, objective
// timing (monolith, golem, elk groups: hitters, bodies near, first capture), deaths by zone, presence by zone, cohesion
// (clusters within 6), contact (opposing bodies within 4) by zone, and stuck metrics with episode lists (idle, A-B-A, loops,
// camp stand-stills without capture, long spawn waits). Zones use walking distances from tools/live/strat_mapgeo.mjs:
// f = d_own / (d_own + d_enemy); own < 0.4, mid 0.4-0.6, enemy > 0.6.
//   CAMBC_CACHE=... MAPGEO=C:/battlecode/cache/an_strategy/mapgeo2.jsonl node tools/live/strat_extract.mjs replay-or-dump...
// (MAPGEO = strat_mapgeo.mjs output fixed by strat_mapgroups.mjs: both sides' camp groups)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { decode } from '../replay/decode.mjs';
// Also reads the compact dumps of tools/live/fightdump.mjs (<name>.json.gz: meta, R, ev) without re-decoding the replay.
async function load(file) {
  if (!file.endsWith('.json.gz')) return decode(fs.readFileSync(file));
  const z = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const team = new Map(z.meta.bodies.map((b) => [b.index, b.team]));
  const rounds = z.R.map(([r, s0, s1, ch]) => ({ r, sub: [s0, s1], ch: ch.map((c) => [c[0], team.get(c[0]), 0, c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], []]) }));
  return { meta: z.meta, rounds, events: z.ev };
}
const GEO = new Map();
for (const l of fs.readFileSync(process.env.MAPGEO || 'C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n')) {
  if (!l.trim()) continue; const g = JSON.parse(l); GEO.set(g.map, g);
}
const WINS = [[1, 150], [150, 400], [400, 800], [800, 2001]];
const CP = [50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800, 2000];
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
for (const file of process.argv.slice(2)) {
  let d;
  const base = path.basename(file).replace(/\.json\.gz$/, '.repl26a');
  try { d = await load(file); } catch (e) { console.log(JSON.stringify({ file: base, err: e.message })); continue; }
  const map = base.replace(/_[0-9a-f]{8}\.repl26a$/, '');
  const geo = GEO.get(map);
  if (!geo) { console.log(JSON.stringify({ file: base, err: 'no geo ' + map })); continue; }
  const W = geo.W, H = geo.H;
  // zone f for team t at (x, y)
  const fAt = (t, x, y) => {
    if (x < 0 || y < 0 || x >= W || y >= H) return null;
    let a = geo.dA[y * W + x], b = geo.dB[y * W + x];
    if (a < 0 || b < 0) return null;
    const f = a / (a + b || 1); return t === 0 ? f : 1 - f;
  };
  const zoneOf = (f) => (f === null ? null : f < 0.4 ? 'own' : f > 0.6 ? 'enemy' : 'mid');
  // groups: tile -> group
  const tileG = new Map();
  for (const g of geo.groups) for (const c of g.camps) tileG.set(c[0] * 1000 + c[1], g.i);
  const groupAt = (x, y) => {
    if (tileG.has(x * 1000 + y)) return tileG.get(x * 1000 + y);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) if (tileG.has((x + dx) * 1000 + y + dy)) return tileG.get((x + dx) * 1000 + y + dy);
    return -1;
  };
  const gcls = (g) => { const ts = new Set(g.camps.map((c) => c[2])); return ts.has('monolith') ? 'mono' : ts.has('golem') ? 'golem' : ts.has('elk') ? 'elk' : ts.has('wolf') ? 'wolf' : ts.has('gem') ? 'gem' : 'gold'; };
  const gzone = (t, g) => { const f = t === 0 ? g.f : 1 - g.f; return zoneOf(f); };
  const bodies = d.meta.bodies;
  const teamOf = (i) => bodies[i]?.team;
  const R = new Map(); for (const s of d.rounds) R.set(s.r, s);
  const final = d.meta.finalRound ?? d.rounds[d.rounds.length - 1].r;
  const posOf = new Map(); // r -> Map(index -> [x, y, hp, maxHp])
  for (const s of d.rounds) { const m = new Map(); for (const c of s.ch) if (c[7] && c[3] >= 0) m.set(c[0], [c[3], c[4], c[5], c[6], c[8]]); posOf.set(s.r, m); }
  const P = (r, i) => posOf.get(r)?.get(i) || null;
  const spawnSet = [new Set(geo.spawnA.map(([x, y]) => x * 1000 + y)), new Set(geo.spawnB.map(([x, y]) => x * 1000 + y))];
  const onSpawn = (t, x, y) => { for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) if (spawnSet[t].has((x + dx) * 1000 + y + dy)) return true; return false; };
  const onSpawnStrict = (t, x, y) => spawnSet[t].has(x * 1000 + y);
  // actions per (r, who)
  const act = new Set(), capd = new Set(), moved = new Set();
  const hitsOnGroup = new Map(); // group -> [{r, who}]
  let blocked = [0, 0];
  // channels keep a body busy: tribute (until banked), recall (5 turns), teleport (until complete)
  const chanEnd = new Map();
  for (const e of d.events) {
    if (e.who === undefined) continue;
    if (e.k === 'Submit gems' || e.k === 'Teleport channel') chanEnd.set(e.who, { r: e.r, k: e.k });
    else if ((e.k === 'Banked' || e.k === 'Gems submitted' || e.k === 'Teleport complete') && chanEnd.has(e.who)) { const s = chanEnd.get(e.who); for (let r = s.r; r <= e.r && r <= s.r + 20; r++) act.add(r * 64 + e.who); chanEnd.delete(e.who); }
    else if (e.k === 'Recall') {
      // busy only for a recall that completes (arrives on spawn within 7 rounds); start-cancel spam at one spot is not an action
      const t = teamOf(e.who), p0 = P(e.r, e.who);
      for (let k = 1; k <= 7; k++) { const p = P(e.r + k, e.who); if (p && p0 && onSpawnStrict(t, p[0], p[1]) && !onSpawnStrict(t, p0[0], p0[1])) { for (let r = e.r; r <= e.r + k; r++) act.add(r * 64 + e.who); break; } }
    }
  }
  for (const e of d.events) {
    if (e.who === undefined) continue;
    if (/Attack|Cast ability|Submit gems|Shop|Place ward|Consumable|Gems submitted|Teleport/.test(e.k)) act.add(e.r * 64 + e.who);
    if (e.k === 'CaptureGems') capd.add(e.r * 64 + e.who);
    if (e.k === 'Move') moved.add(e.r * 64 + e.who);
    if (e.k === 'Movement blocked') blocked[teamOf(e.who)]++;
    if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) {
      const g = tileG.get(e.to[0] * 1000 + e.to[1]);
      if (g !== undefined) { if (!hitsOnGroup.has(g)) hitsOnGroup.set(g, []); hitsOnGroup.get(g).push({ r: e.r, who: e.who }); }
    }
  }
  const out = { file: base, map, W, H, final, outcome: d.meta.outcome, types: [0, 1].map((t) => bodies.filter((b) => b.team === t).map((b) => b.type)), T: {}, caps: [], fights: {} };
  // banked curves
  for (const t of [0, 1]) out.T[t] = { sub: CP.map((r) => (R.get(Math.min(r, final)) || d.rounds[d.rounds.length - 1]).sub[t]) };
  out.subFinal = d.meta.submitted;
  // captures (group-level: same round, same group, same team = one capture)
  const capMap = new Map();
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' || e.who === undefined || !e.at) continue;
    const t = teamOf(e.who); const g = groupAt(e.at[0], e.at[1]);
    const key = `${e.r}:${t}:${g}`;
    if (!capMap.has(key)) capMap.set(key, { r: e.r, t, g, gems: 0, gold: 0, sharers: 0, who: [] });
    const c = capMap.get(key); c.gems += e.gems; c.gold += e.gold || 0; c.sharers++; c.who.push(e.who);
  }
  const lastCapOf = new Map();
  const caps = [...capMap.values()].sort((a, b) => a.r - b.r);
  for (const c of caps) {
    const g = c.g >= 0 ? geo.groups[c.g] : null;
    const cls = g ? gcls(g) : 'unk';
    const zone = g ? gzone(c.t, g) : zoneOf(fAt(c.t, ...(P(c.r, c.who[0]) || [-1, -1])));
    // bodies of the team within 6 of the group centre at the capture round; hitters on the group since its last capture
    let near = 0, enemyNear = 0;
    if (g) for (const [i, p] of posOf.get(c.r) || []) { if (cheb(p[0], p[1], Math.round(g.cx), Math.round(g.cy)) <= 6 + 1) { if (teamOf(i) === c.t) near++; else enemyNear++; } }
    const since = lastCapOf.get(c.g) ?? 0;
    const hitters = new Set(), enemyHitters = new Set(); let firstHit = null;
    for (const h of hitsOnGroup.get(c.g) || []) if (h.r > since && h.r <= c.r) { if (teamOf(h.who) === c.t) { hitters.add(h.who); if (firstHit === null) firstHit = h.r; } else enemyHitters.add(h.who); }
    lastCapOf.set(c.g, c.r);
    out.caps.push({ r: c.r, t: c.t, g: c.g, cls, zone, gems: c.gems, gold: c.gold, sharers: c.sharers, near, enemyNear, hitters: hitters.size, enemyHitters: enemyHitters.size, firstHit });
  }
  // heavy objective attempts (monolith / golem / elk groups): per team, hit episodes (gap > 30 rounds splits) and their outcome
  out.att = [];
  for (const [g, hs] of hitsOnGroup) {
    const G = geo.groups[g]; const cls = gcls(G); if (cls !== 'mono' && cls !== 'golem' && cls !== 'elk') continue;
    for (const t of [0, 1]) {
      const mine = hs.filter((h) => teamOf(h.who) === t).sort((a, b) => a.r - b.r);
      let s0 = null, e0 = null, who = new Set();
      const flush = () => {
        if (s0 === null) return;
        const cap = out.caps.find((c) => c.g === g && c.r >= s0 && c.r <= e0 + 40);
        out.att.push({ g, cls, t, zone: gzone(t, G), s: s0, e: e0, n: who.size, res: cap ? (cap.t === t ? 'won' : 'stolen') : 'none', capR: cap ? cap.r : null });
      };
      for (const h of mine) { if (s0 === null || h.r - e0 > 30) { flush(); s0 = h.r; who = new Set(); } e0 = h.r; who.add(h.who); }
      flush();
    }
  }
  // deaths / kills
  const deaths = d.events.filter((e) => e.k === 'Death');
  for (const t of [0, 1]) {
    const T = out.T[t];
    T.deaths = 0; T.deathsCamp = 0; T.deathZ = { own: 0, mid: 0, enemy: 0 }; T.bagLost = 0; T.deathsEarly = 0;
    for (const e of deaths) if (e.team === t) {
      T.deaths++; if (e.by === 'camp') T.deathsCamp++; T.bagLost += e.bag || 0; if (e.r < 300) T.deathsEarly++;
      const z = zoneOf(fAt(t, e.at[0], e.at[1])); if (z) T.deathZ[z]++;
    }
    T.kills = deaths.filter((e) => e.team !== t && e.by !== 'camp' && typeof e.by === 'number' && teamOf(e.by) === t).length;
    T.blocked = blocked[t];
    T.recallEv = d.events.filter((e) => e.k === 'Recall' && teamOf(e.who) === t).length;
    { const last = new Map(); let n = 0; for (const e of d.events) if (e.k === 'Recall' && teamOf(e.who) === t) { if (e.r - (last.get(e.who) ?? -99) > 6) n++; last.set(e.who, e.r); } T.recalls = n; }
    T.banks = d.events.filter((e) => e.k === 'Banked' && e.team === t).length;
  }
  // presence, cohesion, contact per window
  for (const t of [0, 1]) { out.T[t].pres = {}; out.T[t].coh = {}; }
  out.fights = { contact: {}, contactZ0: { own: 0, mid: 0, enemy: 0 } };
  for (const [a, b] of WINS) {
    const key = `${a}-${b}`;
    let contact = 0, nr = 0;
    const acc = [0, 1].map(() => ({ own: 0, mid: 0, enemy: 0, n: 0, big: 0, ally: 0, alive: 0, rounds: 0, clusters: 0, g3: 0, cent: 0, mhp: 0 }));
    for (let r = a; r < Math.min(b, final + 1); r++) {
      const m = posOf.get(r); if (!m) continue; nr++;
      const byT = [[], []];
      for (const [i, p] of m) byT[teamOf(i)].push([i, p]);
      for (const t of [0, 1]) {
        const A = acc[t], ch = byT[t]; if (!ch.length) continue;
        A.rounds++;
        for (const [, p] of ch) { const z = zoneOf(fAt(t, p[0], p[1])); if (z) { A[z]++; A.n++; } }
        const n = ch.length, par = [...Array(n).keys()];
        const f = (x) => (par[x] === x ? x : (par[x] = f(par[x])));
        for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) if (cheb(ch[p][1][0], ch[p][1][1], ch[q][1][0], ch[q][1][1]) <= 6) par[f(p)] = f(q);
        const sz = {}; for (let p = 0; p < n; p++) sz[f(p)] = (sz[f(p)] || 0) + 1;
        const big = Math.max(...Object.values(sz));
        A.big += big; A.clusters += Object.keys(sz).length; if (big >= 3) A.g3++;
        for (let p = 0; p < n; p++) { A.alive++; if (sz[f(p)] > 1) A.ally++; }
        const mx = ch.reduce((s, c) => s + c[1][0], 0) / n, my = ch.reduce((s, c) => s + c[1][1], 0) / n;
        A.mhp += ch.reduce((s, c) => s + c[1][3], 0) / n;
        A.cent += ch.reduce((s, c) => s + Math.max(Math.abs(c[1][0] - mx), Math.abs(c[1][1] - my)), 0) / n;
      }
      // contact: any opposing pair within 4
      let hit = null;
      for (const [, p] of byT[0]) { for (const [, q] of byT[1]) if (cheb(p[0], p[1], q[0], q[1]) <= 4) { hit = [(p[0] + q[0]) >> 1, (p[1] + q[1]) >> 1]; break; } if (hit) break; }
      if (hit) { contact++; const z = zoneOf(fAt(0, hit[0], hit[1])); if (z) out.fights.contactZ0[z]++; }
    }
    out.fights.contact[key] = nr ? +(contact / nr).toFixed(3) : null;
    for (const t of [0, 1]) {
      const A = acc[t];
      out.T[t].pres[key] = A.n ? [+(A.own / A.n).toFixed(3), +(A.mid / A.n).toFixed(3), +(A.enemy / A.n).toFixed(3)] : null;
      out.T[t].coh[key] = A.rounds ? { big: +(A.big / A.rounds).toFixed(2), ally: +(A.ally / A.alive).toFixed(2), clusters: +(A.clusters / A.rounds).toFixed(2), g3: +(A.g3 / A.rounds).toFixed(2), spread: +(A.cent / A.rounds).toFixed(1), alive: +(A.alive / A.rounds).toFixed(2), mhp: Math.round(A.mhp / A.rounds) } : null;
    }
  }
  // stuck metrics and episodes
  const campTile = (x, y) => tileG.has(x * 1000 + y);
  for (const t of [0, 1]) {
    const S = { idle: 0, aba: 0, abaE: 0, loop: 0, loopE: 0, campStand: 0, campStandE: 0, spawnWait: 0, nb: 0, alive: 0 };
    const eps = [];
    const enemyNear = (r, p, R0 = 8) => { for (const [i, q] of posOf.get(r) || []) if (teamOf(i) !== t && cheb(p[0], p[1], q[0], q[1]) <= R0) return true; return false; };
    for (const b of bodies.filter((b) => b.team === t)) {
      S.nb++;
      let idleRun = 0, idleStart = 0, campRun = 0, campStart = 0, campG = -1, spRun = 0, spStart = 0, abaRun = 0, abaStart = 0;
      const pos = [];
      const closeIdle = (r) => {
        if (idleRun >= 4) {
          let c = false; for (let k = idleStart; k <= r + 1; k++) if (capd.has(k * 64 + b.index)) c = true;
          if (!c) { S.idle += idleRun; if (idleRun >= 10) { const p = P(idleStart, b.index); eps.push({ k: 'idle', who: b.index, ty: b.type, r0: idleStart, len: idleRun, at: p ? [p[0], p[1]] : null, en: p ? enemyNear(idleStart, p) : null, camp: p ? groupAt(p[0], p[1]) : -1 }); } }
        }
        idleRun = 0;
      };
      const closeCamp = (r) => {
        if (campRun >= 8) {
          let c = false; for (let k = campStart; k <= r + 1; k++) if (capd.has(k * 64 + b.index)) c = true;
          if (!c) { S.campStand += campRun; const p = P(campStart, b.index); const en = p ? enemyNear(campStart, p, 10) : false; if (en) S.campStandE += campRun; if (campRun >= 12) eps.push({ k: 'camp', who: b.index, ty: b.type, r0: campStart, len: campRun, at: p ? [p[0], p[1]] : null, en, g: campG, cls: campG >= 0 ? gcls(geo.groups[campG]) : null }); }
        }
        campRun = 0;
      };
      const closeSp = () => { if (spRun >= 3) { S.spawnWait += spRun; if (spRun >= 15) eps.push({ k: 'spawn', who: b.index, ty: b.type, r0: spStart, len: spRun }); } spRun = 0; };
      const closeAba = () => { if (abaRun >= 6) { const p = P(abaStart, b.index); eps.push({ k: 'aba', who: b.index, ty: b.type, r0: abaStart, len: abaRun, at: p ? [p[0], p[1]] : null, en: p ? enemyNear(abaStart, p) : null }); } abaRun = 0; };
      for (let r = 2; r <= final; r++) {
        const p = P(r, b.index), q = P(r - 1, b.index);
        pos.push(p);
        if (p) S.alive++;
        const busy = act.has(r * 64 + b.index);
        const sp = p && onSpawn(t, p[0], p[1]);
        // idle: alive, off spawn, did not move, no action
        if (p && q && p[0] === q[0] && p[1] === q[1] && !busy && !sp) { if (!idleRun) idleStart = r; idleRun++; } else closeIdle(r);
        // camp stand: on a camp tile, not attacking/casting at anything, same group, run
        const g = p && campTile(p[0], p[1]) ? tileG.get(p[0] * 1000 + p[1]) : -1;
        if (g >= 0 && !busy && (campRun === 0 || g === campG)) { if (!campRun) { campStart = r; campG = g; } campRun++; } else { closeCamp(r); if (g >= 0 && !busy) { campStart = r; campG = g; campRun = 1; } }
        // spawn wait: strictly on own spawn, full hp, not moving, not shopping
        if (p && q && onSpawnStrict(t, p[0], p[1]) && p[0] === q[0] && p[1] === q[1] && p[2] >= p[3] && !busy) { if (!spRun) spStart = r; spRun++; } else closeSp();
        // A-B-A
        const p2 = P(r - 2, b.index);
        if (p && q && p2 && p[0] === p2[0] && p[1] === p2[1] && (p[0] !== q[0] || p[1] !== q[1])) { S.aba++; if (enemyNear(r, p)) S.abaE++; if (!abaRun) abaStart = r; abaRun++; } else closeAba();
      }
      closeIdle(final); closeCamp(final); closeSp(); closeAba();
      // loops: 8 moving rounds, net displacement <= 2
      let loopRun = 0, loopStart = 0;
      for (let i = 8; i < pos.length; i++) {
        const a = pos[i - 8], z = pos[i];
        let mv = !!(a && z);
        if (mv) for (let k = i - 7; k <= i; k++) if (!pos[k] || !pos[k - 1] || (pos[k][0] === pos[k - 1][0] && pos[k][1] === pos[k - 1][1])) { mv = false; break; }
        if (mv && cheb(a[0], a[1], z[0], z[1]) <= 2) { S.loop++; if (enemyNear(i + 2, z)) S.loopE++; if (!loopRun) loopStart = i + 2 - 8; loopRun++; }
        else { if (loopRun >= 8) { const p = pos[loopStart - 2]; eps.push({ k: 'loop', who: b.index, ty: b.type, r0: loopStart, len: loopRun + 8, at: p ? [p[0], p[1]] : null }); } loopRun = 0; }
      }
    }
    out.T[t].stuck = S;
    out.T[t].eps = eps.sort((x, y) => y.len - x.len).slice(0, 25);
  }
  console.log(JSON.stringify(out));
}
