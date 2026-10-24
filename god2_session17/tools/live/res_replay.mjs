#!/usr/bin/env node
// Resource flow per body from a replay (gold held, items, max HP, shopping, recalls, banking, gems lost). One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/res_replay.mjs replay...      (or through tools/live/par.py)
// Item ids follow the SDK enum: id = family*6 + stat*2 + emblem; families Monster Power Durability Treasure Jungle Home Bruiser,
// stats strength focus health. Shard equivalents (se) = shards + 5 per emblem (= gold spent on items / 30).
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';

const FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser'];
const STAT = ['str', 'foc', 'hp'];
const CP = [50, 100, 150, 200, 300, 400, 600, 800, 1000, 1200];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

function itemInfo(items) {
  // shard equivalents, stat points per stat, emblems list (id), health se
  let se = 0;
  const pts = [0, 0, 0];
  const emb = [];
  for (const [id, q] of items) {
    const fam = Math.floor(id / 6), stat = Math.floor((id % 6) / 2), isE = id % 2;
    if (isE) {
      se += 5 * q;
      for (let k = 0; k < q; ++k) emb.push(id);
      if (fam === 1) pts[stat] += 6 * q;
      else if (fam === 6) { pts[stat] += 5 * q; for (let s = 0; s < 3; ++s) if (s !== stat) pts[s] += q; }
      else pts[stat] += 5 * q;
    } else {
      se += q;
      pts[stat] += q;
    }
  }
  return { se, pts, emb };
}
const iname = (id) => `${FAM[Math.floor(id / 6)]}-${STAT[Math.floor((id % 6) / 2)]}${id % 2 ? '' : '-shard'}`;

for (const file of process.argv.slice(2)) {
  let d;
  try {
    d = await decode(fs.readFileSync(file), { every: 1 });
  } catch (e) {
    console.error(file, e.message);
    continue;
  }
  const R = new Map(d.rounds.map((s) => [s.r, s]));
  const final = d.meta.finalRound;
  const bodies = d.meta.bodies;
  const snap = (r) => {
    for (let k = r; k >= 0; --k) if (R.has(k)) return R.get(k);
    return d.rounds[0];
  };
  const chOf = (s, idx) => s.ch.find((c) => c[0] === idx);
  // spawn tiles per team: first snapshot positions + positions right after a respawn
  const spawn = [new Set(), new Set()];
  const first = d.rounds[0];
  for (const c of first.ch) spawn[c[1]].add(c[3] + ',' + c[4]);
  for (const e of d.events) if (e.k === 'Respawn' && e.who !== undefined) {
    const s = R.get(e.r);
    const c = s && chOf(s, e.who);
    if (c) spawn[c[1]].add(c[3] + ',' + c[4]);
  }
  const spawnL = spawn.map((S) => [...S].map((k) => k.split(',').map(Number)));
  const dHome = (team, p) => Math.min(...spawnL[team].map((q) => cheb(p, q)));
  const onSpawn = (team, p) => spawn[team].has(p[0] + ',' + p[1]);

  const out = { file: file.split(/[\\/]/).pop(), final, outcome: d.meta.outcome, drafts: d.meta.drafts, w: d.meta.width, h: d.meta.height, bodies: [] };
  const evBy = new Map();
  for (const e of d.events) if (e.who !== undefined) {
    if (!evBy.has(e.who)) evBy.set(e.who, []);
    evBy.get(e.who).push(e);
  }
  const killsBy = new Map();
  for (const e of d.events) if (e.k === 'Death' && typeof e.by === 'number') killsBy.set(e.by, (killsBy.get(e.by) || 0) + 1);

  for (const b of bodies) {
    const idx = b.index, team = b.team;
    const E = evBy.get(idx) || [];
    const B = { idx, team, type: b.type, cp: {}, emblems: [], recalls: [], shops: [], tributes: [], deaths: [], caps: [] };
    // per-round series
    let prev = null, prevInfo = { se: 0, pts: [0, 0, 0], emb: [] };
    let goldSum = [0, 0, 0], goldN = [0, 0, 0], aliveN = 0;
    let earned = 0, earnedCP = {}, spentSe = 0;
    let goldHeldAlive = 0;
    for (let r = 0; r <= final; ++r) {
      const s = R.get(r);
      if (!s) continue;
      const c = chOf(s, idx);
      if (!c) continue;
      const info = itemInfo(c[11]);
      if (prev) {
        const dse = info.se - prevInfo.se;
        const inc = (c[9] - prev[9]) + 30 * dse;
        if (inc > 0) earned += inc;
        // new emblems
        const pe = prevInfo.emb.slice();
        for (const id of info.emb) {
          const k = pe.indexOf(id);
          if (k >= 0) pe.splice(k, 1);
          else B.emblems.push([r, iname(id)]);
        }
      }
      const w = r < 300 ? 0 : r < 600 ? 1 : 2;
      goldSum[w] += c[9]; goldN[w] += 1;
      if (CP.includes(r)) B.cp[r] = { gold: c[9], gems: c[8], maxHp: c[6], hp: c[5], alive: c[7], se: info.se, pts: info.pts, earned };
      prev = c; prevInfo = info;
    }
    B.goldMean = goldSum.map((x, i) => (goldN[i] ? Math.round(x / goldN[i]) : null));
    B.earned = earned;
    B.finalSe = prevInfo.se; B.finalPts = prevInfo.pts;
    B.finalItems = prev ? prev[11].map(([id, q]) => [iname(id), q]) : [];
    B.kills = killsBy.get(idx) || 0;

    // event pass: alive state, recalls, shops, tributes
    let alive = true;
    let lastCap = null; // {r, at}
    const openRecalls = [];
    let openTrib = null;
    const shopRounds = new Map();
    for (const e of E) {
      if (e.k === 'Death') {
        alive = false;
        B.deaths.push({ r: e.r, bag: e.bag, by: e.by === 'camp' ? 'camp' : 'champ', at: e.at, gold: (chOf(snap(e.r - 1), idx) || [])[9] });
        if (openTrib) { openTrib.res = 'death'; B.tributes.push(openTrib); openTrib = null; }
        for (const rc of openRecalls) if (!rc.res && e.r - rc.r <= 7) rc.res = 'death';
      } else if (e.k === 'Respawn') alive = true;
      else if (e.k === 'CaptureGems') { lastCap = { r: e.r, at: e.at }; B.caps.push([e.r, e.gems, e.gold]); }
      else if (e.k === 'Shop') {
        const key = e.r;
        if (!shopRounds.has(key)) shopRounds.set(key, { r: e.r, n: 0, alive });
        shopRounds.get(key).n += 1;
      } else if (e.k === 'Recall') {
        const s0 = snap(e.r - 1);
        const c = chOf(s0, idx);
        const p = [c[3], c[4]];
        openRecalls.push({ r: e.r, hpf: +(c[5] / Math.max(1, c[6])).toFixed(2), gold: c[9], gems: c[8], dh: dHome(team, p), res: null });
      } else if (e.k === 'Submit gems') {
        const s0 = snap(e.r - 1);
        const c = chOf(s0, idx);
        const p = [c[3], c[4]];
        if (openTrib) { openTrib.res = 'restart'; B.tributes.push(openTrib); }
        const alt = e.to || p;
        openTrib = {
          r: e.r, bag: c[8], hpf: +(c[5] / Math.max(1, c[6])).toFixed(2), altarHome: dHome(team, alt),
          capD: lastCap ? cheb(lastCap.at, alt) : null, sinceCap: lastCap ? e.r - lastCap.r : null, capDh: lastCap ? dHome(team, lastCap.at) : null, res: null,
        };
      } else if (e.k === 'Banked') {
        if (openTrib) { openTrib.res = 'ok'; openTrib.dur = e.r - openTrib.r; openTrib.gems = e.gems; B.tributes.push(openTrib); openTrib = null; }
        else B.tributes.push({ r: e.r, res: 'ok-unmatched', gems: e.gems });
      } else if (e.k === 'Cancel channel') {
        if (openTrib && e.r - openTrib.r <= 25) { openTrib.res = 'cancel'; B.tributes.push(openTrib); openTrib = null; }
        else { const rc = openRecalls.find((x) => !x.res && e.r - x.r <= 8); if (rc) rc.res = 'cancel'; }
      }
    }
    if (openTrib) { openTrib.res = 'open'; B.tributes.push(openTrib); }
    // recall outcomes: arrival on spawn within 8 rounds, capture landing around it, what follows
    for (const rc of openRecalls) {
      let arr = null;
      if (!rc.res) {
        for (let r = rc.r; r <= Math.min(final, rc.r + 8); ++r) {
          const c = chOf(R.get(r) || snap(r), idx);
          if (c && c[7] && onSpawn(team, [c[3], c[4]]) && rc.dh > 1) { arr = r; break; }
        }
        rc.res = arr !== null ? 'ok' : (rc.dh <= 1 ? 'onspawn' : 'interrupted');
      }
      rc.arr = arr;
      // capture landing: gems or gold up within [r, r+7] without a kill
      rc.cap = B.caps.some((x) => x[0] >= rc.r - 1 && x[0] <= rc.r + 7);
      if (arr !== null) {
        rc.shop = [...shopRounds.keys()].some((r) => r >= arr && r <= arr + 3);
        rc.bankAfter = B.tributes.find((t) => t.r >= arr && t.r <= arr + 30) ? 1 : 0;
        const c = chOf(snap(arr), idx);
        rc.goldArr = c ? c[9] : null; rc.gemsArr = c ? c[8] : null;
      }
      B.recalls.push(rc);
    }
    // shopping visits: how the body got there
    for (const sv of shopRounds.values()) {
      const s0 = snap(sv.r - 1), s1 = snap(sv.r);
      const c0 = chOf(s0, idx), c1 = chOf(s1, idx);
      const i0 = itemInfo(c0[11]), i1 = itemInfo(c1[11]);
      let how = sv.alive ? 'spawn' : 'dead';
      if (sv.alive) {
        const rec = B.recalls.find((x) => x.arr !== null && x.arr !== undefined && sv.r - x.arr >= 0 && sv.r - x.arr <= 3);
        if (rec) how = 'recall';
        else if (B.deaths.some((x) => sv.r - x.r >= 0 && sv.r - x.r <= 64)) how = 'respawn';
        else if (sv.r <= 3) how = 'start';
        else if (!onSpawn(team, [c0[3], c0[4]]) && !onSpawn(team, [c1[3], c1[4]])) how = 'remote';
        else how = 'walk';
      }
      B.shops.push({ r: sv.r, how, goldBefore: c0[9], dse: i1.se - i0.se, goldAfter: c1[9] });
    }
    B.shops.sort((a, b) => a.r - b.r);
    out.bodies.push(B);
  }
  // team checkpoints: banked
  out.sub = {};
  for (const r of CP) { const s = R.get(r); if (s) out.sub[r] = s.sub; }
  console.log(JSON.stringify(out));
}
