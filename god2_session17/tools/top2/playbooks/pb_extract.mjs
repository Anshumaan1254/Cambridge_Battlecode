#!/usr/bin/env node
// Playbook features per game and team from tools/live/fightdump.mjs dumps (+ map geometry C:/battlecode/cache/an_strategy/mapgeo2.jsonl:
// walking distances from both spawns, camp groups, altars). Zones use the walking-distance share f = d_own / (d_own + d_enemy):
// own < 0.4, mid 0.4-0.6, their > 0.6. Phase windows W1 r1-100, W2 101-300, W3 301-600, W4 601-1000, W5 1001+.
// Per team: per window (presence by zone, activity farm/fight/walk/idle/bank/home, cohesion, captures by zone and camp class,
// deaths, kills, bags, banks, recalls, shops, wards, locks, damage, gold income), checkpoints (score, max-health sum, gold, bags),
// game-level events (first capture / mid capture / kill / contact, round to 500/1000, tributes, final tribute, objectives),
// per-body role summaries. One JSON line per game.
//   node tools/top2/playbooks/pb_extract.mjs dump.json.gz...   (or through tools/live/par.py)
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const GEO = new Map(fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => { const g = JSON.parse(l); return [g.map, g]; }));
const WIN = [[1, 100], [101, 300], [301, 600], [601, 1000], [1001, 99999]];
const wOf = (r) => (r <= 100 ? 0 : r <= 300 ? 1 : r <= 600 ? 2 : r <= 1000 ? 3 : 4);
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
const CLASS = (types) => (types.includes('monolith') ? 'mono' : types.includes('golem') || types.includes(5) || types.includes('5') ? 'golem' : types.includes('elk') ? 'elk' : types.includes('wolf') ? 'wolf' : 'cluster');

function one(file) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const name = path.basename(file).replace(/\.json\.gz$/, '');
  const map = name.replace(/_[0-9a-f]{8}$/, '');
  const g = GEO.get(map);
  const W = d.meta.width, H = d.meta.height;
  const bodies = d.meta.bodies;
  const teamOf = (i) => bodies[i].team;
  const final = d.meta.finalRound;
  // ---- geometry: f0 (team 0 perspective) per tile, spawn test
  const F = new Float32Array(W * H);
  const DO = [new Int32Array(W * H), new Int32Array(W * H)];
  const sp0 = d.R[0][3];
  const spc = [0, 1].map((t) => { const b = sp0.filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
  const pass = (arr, x, y) => x >= 0 && y >= 0 && x < W && y < H && arr[y * W + x] >= 0;
  const dist = (arr, x, y) => {
    if (pass(arr, x, y)) return arr[y * W + x];
    let best = 1e9;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (pass(arr, x + dx, y + dy)) best = Math.min(best, arr[(y + dy) * W + x + dx] + 1);
    return best >= 1e9 ? -1 : best;
  };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let a = g ? dist(g.dA, x, y) : -1, b = g ? dist(g.dB, x, y) : -1;
    if (a < 0 || b < 0) { a = Math.hypot(x - spc[0][0], y - spc[0][1]); b = Math.hypot(x - spc[1][0], y - spc[1][1]); }
    F[y * W + x] = a + b > 0 ? a / (a + b) : 0.5;
    DO[0][y * W + x] = Math.round(a); DO[1][y * W + x] = Math.round(b);
  }
  const fT = (t, x, y) => { const v = F[y * W + x]; return t === 0 ? v : 1 - v; };
  const zone = (t, x, y) => { const v = fT(t, x, y); return v < 0.4 ? 'own' : v <= 0.6 ? 'mid' : 'their'; };
  const atSpawn = (t, x, y) => cheb(x, y, spc[t][0], spc[t][1]) <= 2.6;
  // ---- camp groups
  const camps = d.meta.camps;
  const campAt = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = new Map(camps.map((c) => [c.index, c.index]));
  const find = (i) => { while (par.get(i) !== i) { par.set(i, par.get(par.get(i))); i = par.get(i); } return i; };
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = campAt.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par.set(find(c.index), find(j)); }
  const groups = new Map();
  for (const c of camps) { const r = find(c.index); if (!groups.has(r)) groups.set(r, { id: r, camps: [] }); groups.get(r).camps.push(c); }
  for (const gr of groups.values()) {
    gr.cls = CLASS(gr.camps.map((c) => c.type));
    gr.cx = gr.camps.reduce((a, c) => a + c.x, 0) / gr.camps.length; gr.cy = gr.camps.reduce((a, c) => a + c.y, 0) / gr.camps.length;
    gr.f0 = F[Math.round(gr.cy) * W + Math.round(gr.cx)];
    const fs0 = gr.camps.map((c) => F[c.y * W + c.x]); gr.f0 = fs0.reduce((a, v) => a + v, 0) / fs0.length;
  }
  const campGroup = new Map(camps.map((c) => [c.index, find(c.index)]));
  const groupAtTile = (x, y) => { // capture tile -> group (camp tile itself or nearest group within 2)
    const i = campAt.get(x * 1000 + y);
    if (i !== undefined) return groups.get(find(i));
    let best = null, bd = 3;
    for (const gr of groups.values()) for (const c of gr.camps) { const dd = cheb(c.x, c.y, x, y); if (dd < bd) { bd = dd; best = gr; } }
    return best;
  };
  const gzone = (t, gr) => { const v = t === 0 ? gr.f0 : 1 - gr.f0; return v < 0.4 ? 'own' : v <= 0.6 ? 'mid' : 'their'; };
  // ---- rounds
  const S = new Array(final + 2);
  for (let k = 1; k < d.R.length; k++) { const row = d.R[k]; S[row[0]] = row; }
  for (let r = 1; r <= final; r++) if (!S[r]) S[r] = S[r - 1] || d.R[0];
  const pos = (r, b) => { const row = S[Math.max(1, Math.min(final, r))]; return row[3].find((c) => c[0] === b); };
  const ST = []; // ST[r] = Map body -> c
  for (let r = 0; r <= final; r++) ST[r] = new Map((r === 0 ? d.R[0] : S[r])[3].map((c) => [c[0], c]));
  // ---- per-round action marks
  const mark = new Map(); // key body*100000+r -> set of acts
  const add = (b, r, a) => { const k = b * 100000 + r; if (!mark.has(k)) mark.set(k, new Set()); mark.get(k).add(a); };
  for (const x of d.dmg) { const [, r, a, v] = x; if (a >= 0 && teamOf(a) !== teamOf(v)) add(a, r, 'fight'); }
  for (const x of d.cdmg) add(x[2], x[1], 'farm');
  // tribute channels: Submit gems start -> Banked or cancel
  const tribs = [];
  const evBy = {};
  for (const e of d.ev) { (evBy[e.k] ||= []).push(e); }
  const banked = (evBy.Banked || []);
  for (const e of (evBy['Submit gems'] || [])) {
    const c = ST[Math.max(0, e.r - 1)].get(e.who);
    const bag = c ? c[6] : 0;
    const done = banked.find((b) => b.who === e.who && b.r >= e.r && b.r <= e.r + Math.ceil(bag / 10) + 3);
    const t = teamOf(e.who);
    const alt = e.to || [0, 0];
    tribs.push({ r: e.r, who: e.who, t, bag, done: done ? 1 : 0, endR: done ? done.r : null, zone: zone(t, alt[0], alt[1]), at: alt });
    const end = done ? done.r : e.r + Math.ceil(bag / 10);
    for (let r = e.r; r <= end; r++) add(e.who, r, 'bank');
  }
  // ---- per team accumulators
  const T = [0, 1].map((t) => ({
    team: t, n: bodies.filter((b) => b.team === t).length, types: bodies.filter((b) => b.team === t).map((b) => b.type),
    win: WIN.map(() => ({ aliveBR: 0, deadBR: 0, zone: { own: 0, mid: 0, their: 0 }, act: { farm: 0, fight: 0, walk: 0, idle: 0, bank: 0, home: 0 }, adv: 0,
      coh: 0, cohR: 0, squads: 0, together3: 0, caps: 0, capGems: 0, capGold: 0, capZ: { own: 0, mid: 0, their: 0 }, capC: { cluster: 0, wolf: 0, elk: 0, golem: 0, mono: 0 },
      capCn: { cluster: 0, wolf: 0, elk: 0, golem: 0, mono: 0 },
      deaths: 0, kills: 0, bagLost: 0, bagStolen: 0, banks: 0, bankGems: 0, recallsDone: 0, recallEv: 0, shops: 0, wards: 0, wardZ: { own: 0, mid: 0, their: 0 }, locks: 0,
      dmgOut: 0, dmgIn: 0, campDmg: 0, goldIn: 0, goldSpent: 0, holds: 0, holdR: 0 })),
    cp: {}, ev: {},
  }));
  // presence, activity, cohesion
  for (let r = 1; r <= final; r++) {
    const w = wOf(r);
    for (const t of [0, 1]) {
      const A = T[t].win[w];
      const live = [];
      for (const c of S[r][3]) {
        if (teamOf(c[0]) !== t) continue;
        if (!c[5]) { A.deadBR++; continue; }
        A.aliveBR++;
        const z = zone(t, c[1], c[2]); A.zone[z]++;
        A.adv += fT(t, c[1], c[2]);
        const m = mark.get(c[0] * 100000 + r);
        const p = ST[r - 1].get(c[0]);
        const moved = p && p[5] && (p[1] !== c[1] || p[2] !== c[2]);
        let a;
        if (m && m.has('bank')) a = 'bank'; else if (m && m.has('fight')) a = 'fight'; else if (m && m.has('farm')) a = 'farm';
        else if (moved) a = 'walk'; else if (atSpawn(t, c[1], c[2])) a = 'home'; else a = 'idle';
        A.act[a]++;
        if (!atSpawn(t, c[1], c[2])) live.push(c);
      }
      // clusters within Chebyshev 6
      if (live.length) {
        const seen = new Array(live.length).fill(false); let best = 0, comps = 0;
        for (let i = 0; i < live.length; i++) {
          if (seen[i]) continue; comps++;
          let sz = 0; const st = [i]; seen[i] = true;
          while (st.length) { const k = st.pop(); sz++; for (let j = 0; j < live.length; j++) if (!seen[j] && cheb(live[k][1], live[k][2], live[j][1], live[j][2]) <= 6) { seen[j] = true; st.push(j); } }
          best = Math.max(best, sz);
        }
        A.coh += best; A.cohR++; A.squads += comps; if (best >= 3) A.together3++;
      }
    }
  }
  // gold income / spend per body
  for (let r = 1; r <= final; r++) for (const c of S[r][3]) {
    const p = ST[r - 1].get(c[0]); if (!p) continue;
    const dg = c[7] - p[7]; const A = T[teamOf(c[0])].win[wOf(r)];
    if (dg > 0) A.goldIn += dg; else if (dg < 0) A.goldSpent -= dg;
  }
  // holds: runs >= 10 rounds without move/action off spawn
  for (const b of bodies) {
    const t = b.team; let run = 0, r0 = 0;
    for (let r = 2; r <= final + 1; r++) {
      const c = r <= final ? ST[r].get(b.index) : null, p = ST[r - 1].get(b.index);
      const still = c && p && c[5] && p[5] && c[1] === p[1] && c[2] === p[2] && !atSpawn(t, c[1], c[2]) && !mark.has(b.index * 100000 + r);
      if (still) { if (!run) r0 = r; run++; }
      else { if (run >= 10) { const A = T[t].win[wOf(r0)]; A.holds++; A.holdR += run; } run = 0; }
    }
  }
  // captures
  const capList = [[], []];
  for (const e of (evBy.CaptureGems || [])) {
    const t = e.team; const A = T[t].win[wOf(e.r)];
    const gr = groupAtTile(e.at[0], e.at[1]);
    const cls = gr ? gr.cls : 'cluster'; const z = gr ? gzone(t, gr) : zone(t, e.at[0], e.at[1]);
    A.caps++; A.capGems += e.gems; A.capGold += e.gold; A.capZ[z] += e.gems; A.capC[cls] += e.gems; A.capCn[cls]++;
    const near = S[e.r][3].filter((c) => teamOf(c[0]) === t && c[5] && cheb(c[1], c[2], e.at[0], e.at[1]) <= 6).length;
    const enear = S[e.r][3].filter((c) => teamOf(c[0]) !== t && c[5] && cheb(c[1], c[2], e.at[0], e.at[1]) <= 8).length;
    capList[t].push({ r: e.r, who: e.who, gems: e.gems, gold: e.gold, z, cls, near, enear, g: gr ? gr.id : -1 });
  }
  // deaths / kills
  const deathList = [];
  for (const e of (evBy.Death || [])) {
    const t = teamOf(e.who); const A = T[t].win[wOf(e.r)];
    A.deaths++; A.bagLost += e.bag || 0;
    const killer = typeof e.by === 'number' && e.by >= 0 ? e.by : null;
    if (killer !== null && teamOf(killer) !== t) { const K = T[teamOf(killer)].win[wOf(e.r)]; K.kills++; K.bagStolen += e.bag || 0; }
    const allies = S[Math.max(1, e.r - 1)][3].filter((c) => teamOf(c[0]) === t && c[0] !== e.who && c[5] && cheb(c[1], c[2], e.at[0], e.at[1]) <= 8).length;
    const enem = S[Math.max(1, e.r - 1)][3].filter((c) => teamOf(c[0]) !== t && c[5] && cheb(c[1], c[2], e.at[0], e.at[1]) <= 8).length;
    deathList.push({ r: e.r, who: e.who, t, type: bodies[e.who].type, bag: e.bag || 0, z: zone(t, e.at[0], e.at[1]), killer: killer !== null ? bodies[killer].type : String(e.by), allies, enem });
  }
  // banks
  const bankList = [[], []];
  for (const e of banked) {
    const t = e.team; const A = T[t].win[wOf(e.r)];
    A.banks++; A.bankGems += e.gems;
    bankList[t].push({ r: e.r, who: e.who, type: bodies[e.who].type, gems: e.gems, z: zone(t, e.at[0], e.at[1]) });
  }
  // recalls: raw events and completed teleports (alive both rounds, jump > 2 into own spawn area)
  for (const e of (evBy.Recall || [])) T[teamOf(e.who)].win[wOf(e.r)].recallEv++;
  const recallDone = [[], []];
  for (let r = 2; r <= final; r++) for (const c of S[r][3]) {
    const p = ST[r - 1].get(c[0]); const t = teamOf(c[0]);
    if (p && p[5] && c[5] && cheb(p[1], p[2], c[1], c[2]) > 2 && atSpawn(t, c[1], c[2]) && !atSpawn(t, p[1], p[2])) {
      T[t].win[wOf(r)].recallsDone++; recallDone[t].push({ r, who: c[0], hp: p[3] / Math.max(1, p[4]), from: zone(t, p[1], p[2]), bag: p[6] });
    }
  }
  for (const e of (evBy.Shop || [])) T[teamOf(e.who)].win[wOf(e.r)].shops++;
  for (const e of (evBy['Place ward'] || [])) { const t = teamOf(e.who); const A = T[t].win[wOf(e.r)]; A.wards++; if (e.to) A.wardZ[zone(t, e.to[0], e.to[1])]++; }
  const lockList = [[], []];
  for (const e of (evBy['Place altar lock'] || [])) {
    const t = teamOf(e.who); T[t].win[wOf(e.r)].locks++;
    const alt = e.to || [0, 0];
    const own = tribs.find((x) => x.t === t && Math.abs(x.r - e.r) <= 4 && cheb(x.at[0], x.at[1], alt[0], alt[1]) <= 1);
    const foe = tribs.find((x) => x.t !== t && x.r <= e.r && (x.endR === null ? x.r + Math.ceil(x.bag / 10) : x.endR) >= e.r && cheb(x.at[0], x.at[1], alt[0], alt[1]) <= 1);
    lockList[t].push({ r: e.r, kind: foe ? 'offense' : own ? 'guard' : 'other', foeBag: foe ? foe.bag : 0, z: zone(t, alt[0], alt[1]) });
  }
  for (const x of d.dmg) { const [, r, a, v, amt] = x; if (a >= 0 && teamOf(a) !== teamOf(v)) { T[teamOf(a)].win[wOf(r)].dmgOut += amt; T[teamOf(v)].win[wOf(r)].dmgIn += amt; } }
  for (const x of d.cdmg) T[teamOf(x[2])].win[wOf(x[1])].campDmg += x[4];
  // checkpoints
  for (let cpr = 50; cpr <= 2000; cpr += 50) {
    const r = Math.min(cpr, final);
    for (const t of [0, 1]) {
      const cs = S[r][3].filter((c) => teamOf(c[0]) === t);
      T[t].cp[cpr] = { sub: S[r][1 + t], maxHp: cs.reduce((a, c) => a + c[4], 0), gold: cs.reduce((a, c) => a + c[7], 0), carry: cs.reduce((a, c) => a + c[6], 0), maxBag: Math.max(...cs.map((c) => c[6])), alive: cs.filter((c) => c[5]).length, ended: cpr > final ? 1 : 0 };
    }
  }
  // game-level events
  for (const t of [0, 1]) {
    const E = T[t].ev;
    E.firstCap = capList[t].length ? capList[t][0].r : null;
    const mc = capList[t].find((c) => c.z === 'mid'); E.firstMidCap = mc ? mc.r : null;
    const tc = capList[t].find((c) => c.z === 'their'); E.firstTheirCap = tc ? tc.r : null;
    const fk = deathList.find((x) => x.t !== t && x.killer !== 'camp' && bodies.some((b) => b.type === x.killer && b.team === t)); E.firstKill = fk ? fk.r : null;
    const fd = deathList.find((x) => x.t === t); E.firstDeath = fd ? fd.r : null;
    let r500 = null, r1000 = null;
    for (let r = 1; r <= final; r++) { if (r500 === null && S[r][1 + t] >= 500) r500 = r; if (r1000 === null && S[r][1 + t] >= 1000) { r1000 = r; break; } }
    E.r500 = r500; E.r1000 = r1000;
    // first contact: any team body within 5 of an enemy, both off spawn
    let fc = null;
    for (let r = 1; r <= final && fc === null; r++) {
      const cs = S[r][3];
      for (const a of cs) { if (teamOf(a[0]) !== t || !a[5] || atSpawn(t, a[1], a[2])) continue; for (const b of cs) if (teamOf(b[0]) !== t && b[5] && !atSpawn(1 - t, b[1], b[2]) && cheb(a[1], a[2], b[1], b[2]) <= 5) { fc = r; break; } if (fc !== null) break; }
    }
    E.firstContact = fc;
    // advance at early rounds: mean f of alive bodies at r20, 40, 60, 100
    for (const r of [20, 40, 60, 100, 150]) { if (r > final) continue; const cs = S[r][3].filter((c) => teamOf(c[0]) === t && c[5]); E['adv' + r] = cs.length ? +(cs.reduce((a, c) => a + fT(t, c[1], c[2]), 0) / cs.length).toFixed(3) : null; }
    // opening: first camp hit per body
    const fh = bodies.filter((b) => b.team === t).map((b) => { const x = d.cdmg.find((y) => y[2] === b.index); return x ? x[1] : null; });
    E.firstHitMed = fh.filter((v) => v !== null).sort((a, b) => a - b)[Math.floor(fh.filter((v) => v !== null).length / 2)] ?? null;
    // first group hit by the team: class/zone + how many bodies hit it in r<=60
    const firstC = d.cdmg.find((y) => teamOf(y[2]) === t);
    if (firstC) { const gr = groups.get(campGroup.get(firstC[3])); E.firstGroupCls = gr.cls; E.firstGroupZone = gzone(t, gr); E.firstGroupHitters = new Set(d.cdmg.filter((y) => teamOf(y[2]) === t && y[1] <= firstC[1] + 30 && campGroup.get(y[3]) === gr.id).map((y) => y[2])).size; }
    // tributes
    const tr = tribs.filter((x) => x.t === t);
    E.tribStarts = tr.length; E.tribDone = tr.filter((x) => x.done).length;
    E.bigTrib = tr.filter((x) => x.bag >= 150).map((x) => ({ r: x.r, bag: x.bag, done: x.done, type: bodies[x.who].type, z: x.zone }));
    const bl = bankList[t]; E.lastBank = bl.length ? bl[bl.length - 1] : null;
    E.banksList = bl.map((x) => [x.r, x.gems, x.type[0] + x.type[1], x.z[0]]);
    E.caps = capList[t].map((c) => [c.r, c.gems, c.gold, c.z[0], c.cls[0] + c.cls[1], c.near, c.enear, bodies[c.who].type.slice(0, 3)]);
    E.deaths = deathList.filter((x) => x.t === t).map((x) => [x.r, x.type.slice(0, 4), x.bag, x.z[0], x.killer.slice(0, 4), x.allies, x.enem]);
    E.locks = lockList[t];
    E.recalls = recallDone[t].map((x) => [x.r, bodies[x.who].type.slice(0, 3), +x.hp.toFixed(2), x.from[0], x.bag]);
    // objectives
    E.obj = [];
    for (const gr of groups.values()) {
      if (gr.cls !== 'mono' && gr.cls !== 'golem') continue;
      const hits = d.cdmg.filter((y) => teamOf(y[2]) === t && campGroup.get(y[3]) === gr.id);
      const caps = capList[t].filter((c) => c.g === gr.id);
      const ecaps = capList[1 - t].filter((c) => c.g === gr.id);
      E.obj.push({ cls: gr.cls, z: gzone(t, gr), firstHit: hits.length ? hits[0][1] : null, hitters: new Set(hits.map((y) => y[2])).size, dmg: hits.reduce((a, y) => a + y[4], 0), caps: caps.map((c) => c.r), ecaps: ecaps.map((c) => c.r) });
    }
  }
  // per-body roles
  const roles = bodies.map((b) => {
    const t = b.team; const cl = capList[t].filter((c) => c.who === b.index);
    let maxBag = 0, advS = 0, advN = 0, carryR = 0;
    for (let r = 1; r <= final; r++) { const c = ST[r].get(b.index); if (!c) continue; if (c[6] > maxBag) maxBag = c[6]; if (c[5] && r > 100 && r <= 1000) { advS += fT(t, c[1], c[2]); advN++; } if (c[6] >= 100) carryR++; }
    return {
      i: b.index, t, type: b.type, caps: cl.length, capGems: cl.reduce((a, c) => a + c.gems, 0), capGold: cl.reduce((a, c) => a + c.gold, 0),
      banked: bankList[t].filter((x) => x.who === b.index).reduce((a, x) => a + x.gems, 0), banks: bankList[t].filter((x) => x.who === b.index).length,
      deaths: deathList.filter((x) => x.who === b.index).length, bagLost: deathList.filter((x) => x.who === b.index).reduce((a, x) => a + x.bag, 0),
      kills: deathList.filter((x) => x.t !== t && x.killer === b.type && bodies.some((bb) => bb.type === x.killer && bb.team === t)).length,
      dmgOut: d.dmg.filter((x) => x[2] === b.index && teamOf(x[3]) !== t).reduce((a, x) => a + x[4], 0),
      dmgIn: d.dmg.filter((x) => x[3] === b.index && x[2] >= 0 && teamOf(x[2]) !== t).reduce((a, x) => a + x[4], 0),
      campDmg: d.cdmg.filter((x) => x[2] === b.index).reduce((a, x) => a + x[4], 0),
      maxBag, carryR, adv: advN ? +(advS / advN).toFixed(3) : null, recalls: recallDone[t].filter((x) => x.who === b.index).length,
      shops: (evBy.Shop || []).filter((e) => e.who === b.index).length, wards: (evBy['Place ward'] || []).filter((e) => e.who === b.index).length,
      locks: (evBy['Place altar lock'] || []).filter((e) => e.who === b.index).length,
      finalMaxHp: ST[final].get(b.index)?.[4] ?? null,
    };
  });
  for (const t of [0, 1]) for (const A of T[t].win) A.adv = A.aliveBR ? +(A.adv / A.aliveBR).toFixed(3) : null;
  const geo = g ? { s2s: g.feat.s2s, groups: g.feat.groups, midShare: g.feat.midShare, mono: g.feat.mono, golem: g.feat.golem, altars: g.altars.length, gemRate: g.feat.gemRate, hole: g.feat.hole, wall: g.feat.wall, bush: g.feat.bush } : null;
  return { file: name, map, W, H, final, outcome: d.meta.outcome, submitted: d.meta.submitted, geo, teams: T, roles };
}

for (const f of process.argv.slice(2)) {
  try { console.log(JSON.stringify(one(f))); } catch (e) { console.log(JSON.stringify({ file: path.basename(f), err: String(e.stack || e) })); }
}
