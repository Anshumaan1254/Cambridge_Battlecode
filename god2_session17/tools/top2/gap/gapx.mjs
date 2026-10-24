#!/usr/bin/env node
// gap_g8 main extractor: one decoded game (cache of tools/top2/gap/deccache.mjs) -> one JSON line with, for EACH team (0/1):
//   cp      checkpoints (r50..r1500): captures, captured gems / gold, banked (sub), max-health sum, gold held, item shard-equivalents,
//           carried gems, deaths (camp / champion), kills
//   open    opening: per body first move / first camp hit (round, distance from its start) / first capture / first bank; team firsts;
//           first kill of the game (round, killer, victim, zone, bag, victim activity)
//   tb      body-round time budget per phase (dead, farm, fight, trib, recall, oncamp, walk, spawn, idle; nearE_* = with an enemy
//           champion within 8; walkNearEnemy)
//   walks   walk rounds per body labelled by the next action (farm, fight, capture, bank, recall, shop, died, none), r < 1000
//   zones   captures and gems by zone (O own half / M middle band / T their half), per phase
//   kinds   captures by group kind (cluster, wolf, elk, golem, monolith) with gems; objective (golem / monolith) hit rounds, first capture
//   cyc     farming cycles per zone (wait, kill, capture, respawn) for groups this team captured
//   eff     camp efforts (runs of hits on one group, gaps <= 15, >= 3 hits): own / stolen / abandoned (+ enemy within 8 at the last hit,
//           hitter died within 10 rounds), hits wasted
//   mv      movement: A-B-A rounds, loops (8 moving rounds, net <= 2), idle runs >= 4 off spawn not ending in a capture,
//           stand-stills >= 40 rounds (count, rounds, on a camp tile), spawn-idle rounds (alive, on spawn, not acting, beyond 3 rounds)
//   rec     recalls: starts, completed, interrupted, killed; with an enemy within 6 at the start
//   bank    tribute starts, completions, banks (Banked events) and gems, bag lost at deaths, body-rounds carrying >= 50 / 100 / 200
//   deaths  [r, type, by ('camp' | killer type), zone, bag, mode, hp3, al6, en6, al8, en8, myMax, enMaxMean, hpWithin8 ours, theirs]
//   CAMBC_CACHE not needed.   node tools/top2/gap/gapx.mjs DEC.json.gz   (or via tools/live/par.py)
import { loadDec, spawns, spawnTiles, zoneFn, groups, cheb, phaseOf, gameName } from './lib.mjs';

const file = process.argv[2];
let d;
try { d = loadDec(file); } catch (e) { console.log(JSON.stringify({ file: gameName(file), err: String(e) })); process.exit(0); }
const FR = d.meta.finalRound;
const B = d.meta.bodies;
const NB = B.length;
const teamOf = (i) => B[i].team;
const sp = spawns(d), spT = spawnTiles(d), zone = zoneFn(sp);
const onSpawn = (t, x, y) => spT[t].some(([a, b]) => Math.max(Math.abs(a - x), Math.abs(b - y)) <= 1);
const { G, gOf } = groups(d);
const campAt = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
// ST[r][b] = [x, y, hp, maxHp, alive, gems, gold, kills, items]
const ST = [];
for (let r = 0; r <= FR; r++) {
  const s = d.rounds[r] && d.rounds[r].r === r ? d.rounds[r] : null;
  const a = new Array(NB).fill(null);
  if (s) for (const c of s.ch) a[c[0]] = [c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10], c[11]];
  ST.push(s ? a : (ST[r - 1] || a));
}
const P = (r, b) => ST[Math.max(1, Math.min(FR, r))][b];
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const TB = [0, 1].map((t) => B.filter((b) => b.team === t).map((b) => b.index));

// ---- per body-round actions
const key = (b, r) => b * 100000 + r;
const act = new Map();     // 'farm' | 'fight'
const moved = new Set();
const other = new Map();   // first other action label in that round
const evBy = new Map();    // body -> events sorted
for (const e of d.events) {
  if (e.who === undefined) continue;
  if (!evBy.has(e.who)) evBy.set(e.who, []);
  evBy.get(e.who).push(e);
  const k = key(e.who, e.r);
  if (e.k === 'Move') { moved.add(k); continue; }
  if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) {
    if (campAt.has(e.to[0] * 1000 + e.to[1])) { if (!act.has(k)) act.set(k, 'farm'); }
    else {
      const t = teamOf(e.who);
      const hit = [e.r - 1, e.r].some((rr) => { const s = ST[Math.max(1, Math.min(FR, rr))]; return s.some((c, i) => c && c[4] && teamOf(i) !== t && c[0] === e.to[0] && c[1] === e.to[1]); });
      if (hit) act.set(k, 'fight');
      else moved.add(k); // ground cast (dash, area) with no champion on the tile: travelling
    }
    continue;
  }
  let lab = null;
  if (e.k === 'Submit gems') lab = 'bank';
  else if (e.k === 'Shop') lab = 'shop';
  else if (e.k === 'CaptureGems') lab = 'capture';
  else if (e.k === 'Death') lab = 'died';
  else if (e.k === 'Recall') lab = 'recall';
  if (lab && !other.has(k)) other.set(k, lab);
}
// channels: tribute (Submit gems -> Gems submitted / cancel / death), recall (Recall -> on spawn / cancel / death / damage)
const chan = new Map(); // key -> 'trib' | 'recall'
const rec = [{ starts: 0, done: 0, killed: 0, interrupted: 0, nearE: 0, nearE_done: 0 }, { starts: 0, done: 0, killed: 0, interrupted: 0, nearE: 0, nearE_done: 0 }];
const bank = [0, 1].map(() => ({ tribStarts: 0, tribDone: 0, banks: 0, banked: 0, firstBank: null, bankSizes: [], lostAtDeath: 0, bag50: 0, bag100: 0, bag200: 0, maxBag: 0 }));
for (const [b, evs] of evBy) {
  const t = teamOf(b);
  for (let i = 0; i < evs.length; i++) {
    const e = evs[i];
    if (e.k === 'Submit gems') {
      bank[t].tribStarts++;
      let end = Math.min(FR, e.r + 40);
      for (let j = i + 1; j < evs.length; j++) { const f = evs[j]; if (f.r < e.r) continue; if (f.k === 'Gems submitted' || f.k === 'Cancel channel' || f.k === 'Death' || f.k === 'Move' || f.k === 'Attack') { end = f.r; break; } }
      for (let r = e.r; r <= end; r++) if (!chan.has(key(b, r))) chan.set(key(b, r), 'trib');
    } else if (e.k === 'Gems submitted') bank[t].tribDone++;
    else if (e.k === 'Banked') { bank[t].banks++; bank[t].banked += e.gems; bank[t].bankSizes.push(e.gems); if (bank[t].firstBank === null || e.r < bank[t].firstBank) bank[t].firstBank = e.r; }
    else if (e.k === 'Recall') {
      const me = P(e.r - 1, b);
      if (!me || !me[4] || onSpawn(t, me[0], me[1])) continue;
      // a recall start (skip repeats while the channel runs)
      const prevRec = evs.slice(Math.max(0, i - 6), i).some((f) => f.k === 'Recall' && e.r - f.r <= 5 && f.r < e.r);
      if (prevRec) continue;
      rec[t].starts++;
      const foe = ST[Math.max(1, e.r - 1)].some((c, k) => c && c[4] && teamOf(k) !== t && cheb([c[0], c[1]], [me[0], me[1]]) <= 6);
      if (foe) rec[t].nearE++;
      let res = 'interrupted';
      for (let r = e.r; r <= e.r + 7 && r <= FR; r++) {
        const c = P(r, b);
        if (!c) continue;
        if (!c[4]) { res = 'killed'; break; }
        if (onSpawn(t, c[0], c[1])) { res = 'done'; break; }
        chan.set(key(b, r), 'recall');
      }
      rec[t][res]++;
      if (foe && res === 'done') rec[t].nearE_done++;
    }
  }
}
// ---- captures (deduplicated: split rewards share group + round + team)
const caps = [];
{
  const seen = new Map();
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' || !e.at || e.who === undefined) continue;
    const g = gOf(e.at[0], e.at[1]);
    const t = teamOf(e.who);
    const k = `${g}:${e.r}:${t}`;
    if (seen.has(k)) { const c = seen.get(k); c.gems += e.gems; c.gold += Math.max(0, e.gold); c.n++; continue; }
    const c = { r: e.r, g, team: t, gems: e.gems, gold: Math.max(0, e.gold), n: 1, who: e.who, at: e.at };
    seen.set(k, c); caps.push(c);
  }
}
const deathsAll = d.events.filter((e) => e.k === 'Death' && e.who !== undefined);
const out = { file: gameName(file), FR, outcome: d.meta.outcome, sub: d.meta.submitted, W: d.meta.width, H: d.meta.height, nb: TB.map((x) => x.length),
  types: TB.map((x) => x.map((i) => B[i].type)), groups: { n: G.size, kinds: {} }, T: {} };
for (const g of G.values()) out.groups.kinds[g.kind] = (out.groups.kinds[g.kind] || 0) + 1;
// groups by zone relative to team 0 (for map description)
out.groups.zones0 = { O: 0, M: 0, T: 0 };
for (const g of G.values()) out.groups.zones0[zone(0, g.x, g.y)]++;

const itemSE = (items) => { let se = 0; for (const [id, q] of items || []) se += (id % 2 ? 5 : 1) * q; return se; };
const CP = [50, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1200, 1500];
for (const t of [0, 1]) {
  const T = {};
  out.T[t] = T;
  // checkpoints
  T.cp = {};
  for (const r of CP) {
    if (r > FR) break;
    const s = ST[r];
    const mine = TB[t].map((b) => s[b]).filter(Boolean);
    const cs = caps.filter((c) => c.team === t && c.r <= r);
    T.cp[r] = {
      caps: cs.length, capGems: cs.reduce((a, c) => a + c.gems, 0), capGold: cs.reduce((a, c) => a + c.gold, 0),
      banked: d.rounds[r].sub ? d.rounds[r].sub[t] : 0,
      maxHp: mine.reduce((a, c) => a + c[3], 0), gold: mine.reduce((a, c) => a + c[6], 0), se: mine.reduce((a, c) => a + itemSE(c[8]), 0),
      bag: mine.reduce((a, c) => a + (c[4] ? c[5] : 0), 0), alive: mine.filter((c) => c[4]).length,
      deaths: deathsAll.filter((e) => e.team === t && e.r <= r).length, campDeaths: deathsAll.filter((e) => e.team === t && e.r <= r && e.by === 'camp').length,
      kills: mine.reduce((a, c) => a + c[7], 0),
    };
  }
  // opening per body
  T.open = { bodies: [] };
  for (const b of TB[t]) {
    const st = P(1, b);
    const o = { type: B[b].type, firstMove: null, firstHit: null, hitDist: null, hitKind: null, firstCap: null, firstBank: null, firstDeath: null, firstShop: null };
    for (const e of evBy.get(b) || []) {
      if (e.k === 'Move' && o.firstMove === null) o.firstMove = e.r;
      if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to && campAt.has(e.to[0] * 1000 + e.to[1]) && o.firstHit === null) {
        o.firstHit = e.r; o.hitDist = cheb(e.to, [st[0], st[1]]);
        const g = G.get(gOf(e.to[0], e.to[1])); o.hitKind = g ? g.kind : null;
      }
      if (e.k === 'CaptureGems' && o.firstCap === null) o.firstCap = e.r;
      if (e.k === 'Banked' && o.firstBank === null) o.firstBank = e.r;
      if (e.k === 'Death' && o.firstDeath === null) o.firstDeath = e.r;
      if (e.k === 'Shop' && o.firstShop === null) o.firstShop = e.r;
    }
    T.open.bodies.push(o);
  }
  const mn = (k) => { const v = T.open.bodies.map((o) => o[k]).filter((x) => x !== null); return v.length ? Math.min(...v) : null; };
  T.open.firstHit = mn('firstHit'); T.open.firstCap = caps.find((c) => c.team === t)?.r ?? null; T.open.firstBank = bank[t].firstBank;
  T.open.firstMidCap = caps.find((c) => c.team === t && zone(t, c.at[0], c.at[1]) === 'M')?.r ?? null;
  // time budget per phase
  const TBK = ['dead', 'farm', 'fight', 'trib', 'recall', 'oncamp', 'walk', 'spawn', 'idle', 'walkNearEnemy', 'nearE', 'nearE_farm', 'nearE_fight', 'nearE_walk', 'nearE_oncamp', 'nearE_idle', 'nearE_spawn', 'nearE_trib', 'nearE_recall', 'nearE_hpAdv', 'mid', 'mid_farm'];
  T.tb = [0, 1, 2, 3].map(() => Object.fromEntries(TBK.map((k) => [k, 0])));
  for (let r = 2; r <= FR; r++) {
    const ph = phaseOf(r);
    const s = ST[r], p = ST[r - 1];
    for (const b of TB[t]) {
      const c = s[b], o = p[b];
      if (!c) continue;
      const X = T.tb[ph];
      if (!c[4]) { X.dead++; continue; }
      const k = key(b, r);
      const mv = o && o[4] && (o[0] !== c[0] || o[1] !== c[1]);
      let a = act.get(k) || chan.get(k) || (mv ? 'walk' : campAt.has(c[0] * 1000 + c[1]) ? 'oncamp' : onSpawn(t, c[0], c[1]) ? 'spawn' : 'idle');
      X[a]++;
      if (zone(t, c[0], c[1]) === 'M') { X.mid++; if (a === 'farm') X.mid_farm++; }
      let near = false, mine = 0, theirs = 0;
      for (let i = 0; i < NB; i++) {
        const q = s[i];
        if (!q || !q[4] || cheb([q[0], q[1]], [c[0], c[1]]) > 8) continue;
        if (teamOf(i) === t) mine += q[2]; else { near = true; theirs += q[2]; }
      }
      if (near) { X.nearE++; X['nearE_' + a]++; if (a === 'walk') X.walkNearEnemy++; if (mine > theirs) X.nearE_hpAdv++; }
    }
  }
  // walks (r < 1000): runs of walk rounds labelled by the next action of the body
  T.walks = { farm: 0, fight: 0, capture: 0, bank: 0, recall: 0, shop: 0, died: 0, none: 0, n: 0 };
  for (const b of TB[t]) {
    let run = 0;
    for (let r = 2; r < Math.min(1000, FR); r++) {
      const k = key(b, r);
      const a = act.get(k) || other.get(k);
      if (a) { if (run) { T.walks[a] = (T.walks[a] || 0) + run; T.walks.n++; } run = 0; continue; }
      const c = P(r, b), o = P(r - 1, b);
      if (c && c[4] && o && o[4] && (o[0] !== c[0] || o[1] !== c[1])) run++;
      else if (run && !(c && c[4])) { T.walks.died += run; run = 0; }
    }
    if (run) T.walks.none += run;
  }
  // captures by zone and phase, by group kind
  T.zones = [0, 1, 2, 3].map(() => ({ O: [0, 0], M: [0, 0], T: [0, 0] }));
  T.kinds = {};
  for (const c of caps.filter((c) => c.team === t)) {
    const z = zone(t, c.at[0], c.at[1]);
    const X = T.zones[phaseOf(c.r)][z]; X[0]++; X[1] += c.gems;
    const g = G.get(c.g); const kd = g ? g.kind : '?';
    if (!T.kinds[kd]) T.kinds[kd] = { caps: 0, gems: 0, gold: 0, first: c.r };
    T.kinds[kd].caps++; T.kinds[kd].gems += c.gems; T.kinds[kd].gold += c.gold;
  }
  // objective hit rounds (golem / monolith groups)
  T.obj = { golemHits: 0, monoHits: 0, golemHitters: 0, monoHitters: 0, campDeathsNearObj: 0 };
  {
    const hitters = { golem: new Set(), monolith: new Set() };
    for (const b of TB[t]) for (const e of evBy.get(b) || []) {
      if ((e.k !== 'Attack' && e.k !== 'Cast ability') || !e.to) continue;
      const g = G.get(gOf(e.to[0], e.to[1]));
      if (!g) continue;
      if (g.kind === 'golem') { T.obj.golemHits++; hitters.golem.add(`${b}:${Math.floor(e.r / 50)}`); }
      if (g.kind === 'monolith') { T.obj.monoHits++; hitters.monolith.add(`${b}:${Math.floor(e.r / 50)}`); }
    }
    T.obj.golemHitters = hitters.golem.size; T.obj.monoHitters = hitters.monolith.size;
  }
  // farming cycles (port of tools/live/grp_cycles.mjs), only cycles captured by this team
  T.cyc = { O: [], M: [], T: [] };
  // camp efforts (port of tools/live/abandon.mjs + context)
  T.eff = [0, 1, 2, 3].map(() => ({ own: 0, stolen: 0, aband: 0, hitsAband: 0, hitsStolen: 0, hitsOwn: 0, abandEnemyNear: 0, abandDied: 0, abandCampOnly: 0 }));
  {
    const hits = new Map();
    for (const b of TB[t]) for (const e of evBy.get(b) || []) {
      if ((e.k !== 'Attack' && e.k !== 'Cast ability') || !e.to) continue;
      const g = gOf(e.to[0], e.to[1]);
      if (g < 0) continue;
      if (!hits.has(g)) hits.set(g, []);
      hits.get(g).push({ r: e.r, b });
    }
    for (const [g, hs] of hits) {
      hs.sort((a, b) => a.r - b.r);
      let s = 0;
      for (let k = 1; k <= hs.length; k++) {
        if (k < hs.length && hs[k].r - hs[k - 1].r <= 15) continue;
        const a = hs[s].r, z = hs[k - 1].r, n = k - s, last = hs[k - 1];
        s = k;
        if (n < 3) continue;
        const X = T.eff[phaseOf(a)];
        const c = caps.find((c) => c.g === g && c.r >= a && c.r <= z + 30);
        if (!c) {
          X.aband++; X.hitsAband += n;
          const me = P(last.r, last.b);
          const en = me && ST[last.r].some((q, i) => q && q[4] && teamOf(i) !== t && cheb([q[0], q[1]], [me[0], me[1]]) <= 8);
          const died = deathsAll.some((e) => e.who === last.b && e.r >= last.r && e.r <= last.r + 10);
          if (en) X.abandEnemyNear++; if (died) X.abandDied++; if (!en && !died) X.abandCampOnly++;
        } else if (c.team === t) { X.own++; X.hitsOwn += n; } else { X.stolen++; X.hitsStolen += n; }
      }
    }
  }
  // movement pathologies
  T.mv = { aba: 0, abaE: 0, loops: 0, loopsE: 0, idleRuns: 0, stand40: 0, stand40r: 0, stand40camp: 0, stand40max: 0, spawnIdle: 0, spawnIdleMax: 0, longWalk: 0 };
  for (const b of TB[t]) {
    let run = 0, runStart = 0, stand = 0, standAt = null, standStart = 0, sIdle = 0;
    const pos = [];
    for (let r = 2; r <= FR; r++) {
      const p = alive(r, b) ? P(r, b) : null, q = alive(r - 1, b) ? P(r - 1, b) : null;
      pos.push(p);
      const k = key(b, r);
      const busy = act.has(k) || other.has(k) || chan.has(k);
      const sp_ = p && onSpawn(t, p[0], p[1]);
      const still = p && q && p[0] === q[0] && p[1] === q[1];
      // idle runs (stuck.mjs): still, not acting, off spawn, run >= 4 not ending in a capture
      if (still && !busy && !sp_) { if (!run) runStart = r; run++; }
      else {
        if (run >= 4) { let capd = false; for (let x = runStart; x <= r + 1; x++) if (other.get(key(b, x)) === 'capture') capd = true; if (!capd) T.mv.idleRuns += run; }
        run = 0;
      }
      // spawn idle: alive on spawn, still, not acting, beyond the first 3 rounds of a stay
      if (still && sp_ && !act.has(k) && !chan.has(k)) { sIdle++; if (sIdle > 3) T.mv.spawnIdle++; T.mv.spawnIdleMax = Math.max(T.mv.spawnIdleMax, sIdle); } else sIdle = 0;
      // stand-stills >= 40 at one tile off spawn (longstand.mjs, any reason)
      if (p && standAt && p[0] === standAt[0] && p[1] === standAt[1]) stand++;
      else {
        if (stand >= 40 && standAt && !onSpawn(t, standAt[0], standAt[1])) { T.mv.stand40++; T.mv.stand40r += stand; T.mv.stand40max = Math.max(T.mv.stand40max, stand); if (campAt.has(standAt[0] * 1000 + standAt[1])) T.mv.stand40camp++; }
        stand = p ? 1 : 0; standAt = p ? [p[0], p[1]] : null; standStart = r;
      }
      const p2 = alive(r - 2, b) ? P(r - 2, b) : null;
      if (p && q && p2 && p[0] === p2[0] && p[1] === p2[1] && (p[0] !== q[0] || p[1] !== q[1])) {
        T.mv.aba++;
        if (ST[r].some((c, i) => c && c[4] && teamOf(i) !== t && cheb([c[0], c[1]], [p[0], p[1]]) <= 8)) T.mv.abaE++;
      }
    }
    if (stand >= 40 && standAt && !onSpawn(t, standAt[0], standAt[1])) { T.mv.stand40++; T.mv.stand40r += stand; T.mv.stand40max = Math.max(T.mv.stand40max, stand); if (campAt.has(standAt[0] * 1000 + standAt[1])) T.mv.stand40camp++; }
    for (let i = 8; i < pos.length; i++) {
      const a = pos[i - 8], z = pos[i];
      if (!a || !z) continue;
      let mvd = true;
      for (let k = i - 7; k <= i; k++) if (!pos[k] || !pos[k - 1] || (pos[k][0] === pos[k - 1][0] && pos[k][1] === pos[k - 1][1])) { mvd = false; break; }
      if (mvd && cheb(a, z) <= 2) {
        T.mv.loops++;
        const r = i + 2;
        if (ST[Math.min(FR, r)].some((c, j) => c && c[4] && teamOf(j) !== t && cheb([c[0], c[1]], [z[0], z[1]]) <= 8)) T.mv.loopsE++;
      }
    }
  }
  T.rec = rec[t];
  T.bank = bank[t];
  // bag exposure
  for (let r = 1; r <= FR; r++) for (const b of TB[t]) {
    const c = ST[r][b];
    if (!c || !c[4]) continue;
    if (c[5] >= 50) T.bank.bag50++; if (c[5] >= 100) T.bank.bag100++; if (c[5] >= 200) T.bank.bag200++;
    T.bank.maxBag = Math.max(T.bank.maxBag, c[5]);
  }
  // deaths with context
  T.deaths = [];
  for (const e of deathsAll.filter((e) => e.team === t)) {
    T.bank.lostAtDeath += e.bag || 0;
    const me = P(e.r - 1, e.who);
    const by = e.by === 'camp' ? 'camp' : (typeof e.by === 'number' && B[e.by] ? B[e.by].type : String(e.by));
    let fight = 0, farm = 0, move = 0, chn = 0;
    for (let r = e.r - 3; r < e.r; r++) {
      const k = key(e.who, r);
      const a = act.get(k);
      if (a === 'fight') fight++; else if (a === 'farm') farm++; else if (chan.has(k)) chn++; else if (moved.has(k)) move++;
    }
    const mode = fight ? 'fight' : farm ? 'farm' : chn ? 'channel' : move ? 'move' : 'idle';
    const m3 = P(e.r - 3, e.who);
    let al6 = 0, en6 = 0, al8 = 0, en8 = 0, hpO = 0, hpT = 0, enMax = 0, enN = 0;
    if (me && me[4]) {
      for (let i = 0; i < NB; i++) {
        const q = ST[Math.max(1, e.r - 1)][i];
        if (!q || !q[4]) continue;
        const dd = cheb([q[0], q[1]], [me[0], me[1]]);
        const ally = teamOf(i) === t;
        if (dd <= 8) { if (ally) hpO += q[3]; else hpT += q[3]; }
        if (i === e.who) continue;
        if (dd <= 6) { if (ally) al6++; else en6++; }
        if (dd <= 8) { if (ally) al8++; else { en8++; enMax += q[3]; enN++; } }
      }
    }
    const z = me ? zone(t, me[0], me[1]) : '?';
    const nearTheirSpawn = me ? cheb([me[0], me[1]], sp[1 - t]) <= 8 : false;
    T.deaths.push([e.r, B[e.who].type, by, z + (nearTheirSpawn ? 'S' : ''), e.bag || 0, mode, m3 && m3[3] ? +(m3[2] / m3[3]).toFixed(2) : null, al6, en6, al8, en8,
      me ? me[3] : 0, enN ? Math.round(enMax / enN) : 0, hpO, hpT]);
  }
}
// farming cycles (needs both teams' captures)
for (const g of G.values()) {
  const cs = g.camps;
  const maxHp = cs.map((c) => c.hp);
  const gc = caps.filter((c) => c.g === g.id).sort((a, b) => a.r - b.r);
  let state = 'full', tFull = 1, tHit = null, tDead = null, ci = 0, pending = null;
  for (let r = 1; r <= FR; r++) {
    const s = d.rounds[r];
    if (!s || !s.campHp) continue;
    const hp = cs.map((c) => s.campHp[c.index]);
    const full = hp.every((h, k) => h >= maxHp[k] && maxHp[k] > 0);
    const dead = hp.every((h) => h <= 0);
    if (state === 'full' && !full) { state = 'hit'; tHit = r; }
    if (state === 'hit' && full) { state = 'full'; tFull = r; tHit = null; }
    if (state === 'hit' && dead) { state = 'dead'; tDead = r; }
    if (state === 'dead' && ci < gc.length && gc[ci].r <= r) {
      pending = { team: gc[ci].team, zone: zone(gc[ci].team, g.x, g.y), kind: g.kind, wait: tHit - tFull, kill: tDead - tHit, cap: gc[ci].r - tDead, respawn: null, tCap: gc[ci].r };
      ci++; state = 'respawning';
    }
    if (state === 'respawning' && full) { pending.respawn = r - pending.tCap; out.T[pending.team].cyc[pending.zone].push([pending.kind, pending.wait, pending.kill, pending.cap, pending.respawn]); pending = null; state = 'full'; tFull = r; }
  }
  if (pending) out.T[pending.team].cyc[pending.zone].push([pending.kind, pending.wait, pending.kill, pending.cap, null]);
}
// first kill of the game
{
  const fk = deathsAll.find((e) => typeof e.by === 'number');
  if (fk) {
    const me = P(fk.r - 1, fk.who);
    const vt = fk.team;
    const fdeath = out.T[vt].deaths.find((x) => x[0] === fk.r && x[1] === B[fk.who].type);
    out.firstKill = { r: fk.r, killerTeam: teamOf(fk.by), killer: B[fk.by].type, victim: B[fk.who].type, victimTeam: vt, zoneVictim: me ? zone(vt, me[0], me[1]) : '?', bag: fk.bag,
      mode: fdeath ? fdeath[5] : null, al6: fdeath ? fdeath[7] : null, en6: fdeath ? fdeath[8] : null, myMax: fdeath ? fdeath[11] : null, enMax: fdeath ? fdeath[12] : null };
  } else out.firstKill = null;
}
console.log(JSON.stringify(out));
