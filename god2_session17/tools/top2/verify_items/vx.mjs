#!/usr/bin/env node
// verify_items: independent replay pass (engine timeline, one step at a time) for item / gold / max-HP / death checks.
//   CAMBC_CACHE=... node tools/top2/verify_items/vx.mjs replay.repl26a  -> one JSON line
// Per body: purchases in exact step order ([round, itemId, dQty] from item diffs at Shop / Consumable / Sell steps), emblem
// completions in order, checkpoints {300,400,600,1000,final}: maxHp, alive, gold, gems, cumulative gold spent on items / consumables,
// stat points [str, foc, hp] (Power emblem = 6, Bruiser emblem = 5 + 1 + 1, others 5, shard = 1), alive rounds, deaths (round, bag).
// Item id = family*6 + stat*2 + isEmblem (families Monster Power Durability Treasure Jungle Home Bruiser; stats str foc hp).
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, CHAMP } from '../../replay/decode.mjs';

process.removeAllListeners('warning');
const NITEM = 42;
const CPS = [300, 400, 600, 1000];

function pts(items) {
  const p = [0, 0, 0];
  for (let id = 0; id < NITEM; ++id) {
    const q = items[id]; if (!q) continue;
    const fam = Math.floor(id / 6), st = Math.floor((id % 6) / 2), em = id % 2;
    if (!em) { p[st] += q; continue; }
    if (fam === 1) p[st] += 6 * q;
    else if (fam === 6) { p[st] += 5 * q; for (let s = 0; s < 3; ++s) if (s !== st) p[s] += q; }
    else p[st] += 5 * q;
  }
  return p;
}
const value = (items) => { let v = 0; for (let id = 0; id < NITEM; ++id) v += (items[id] || 0) * (id % 2 ? 150 : 30); return v; };

async function run(wasmPath, buf) {
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst);
  const X = inst.exports;
  const out = X.Engine_Malloc(64);
  const dv = () => new DataView(X.memory.buffer);
  const chk = (r, w) => { if (r !== 0) throw new Error(w + ' code ' + r); };
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load');
  const game = dv().getBigUint64(out, true);
  X.Engine_Free(p);
  if (X.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw new Error('layout');
  const snap = X.Engine_Malloc(40152), args = X.Engine_Malloc(128);
  chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main');
  const main = dv().getBigUint64(out, true);
  chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'info');
  const size = dv().getUint32(args, true);
  chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');
  const hdr = () => {
    chk(X.Game_Visualiser_ReadTimelineState(game, snap), 'read');
    const e = dv(), u = (n) => e.getUint32(snap + n, true);
    return { phase: u(24), outcome: u(28), awaiting: u(20), inPos: u(56), kind: u(68), akind: u(72), aidx: u(76), round: u(96), sub: u(104) };
  };
  const champs = () => {
    const e = dv(), u = (n) => e.getUint32(snap + n, true), f = (n) => e.getFloat32(snap + n, true);
    const n = u(172), res = [];
    for (let k = 0; k < n; ++k) {
      const b = 196 + k * 252;
      const items = new Array(NITEM);
      for (let i = 0; i < NITEM; ++i) items[i] = u(b + 48 + i * 4);
      res.push({ index: u(b + 4), team: u(b + 8), type: u(b + 12), maxHp: Math.round(f(b + 28)), alive: u(b + 32), gold: u(b + 36), gems: u(b + 40),
        items, cons: [u(b + 216), u(b + 220), u(b + 224), u(b + 228)] });
    }
    return res;
  };
  let h = hdr();
  let bodies = null, B = null, lastRound = -1, guard = 0, endState = null;
  const ensure = () => {
    if (B) return;
    const cs = champs();
    bodies = cs.map((c) => ({ index: c.index, team: c.team, type: CHAMP[c.type] ?? c.type }));
    B = new Map(cs.map((c) => [c.index, { items: c.items.slice(), cons: c.cons.slice(), gold: c.gold, alive: c.alive, spentItems: 0, spentCons: 0,
      buys: [], emb: [], cp: {}, aliveRounds: 0, deaths: [], gems: c.gems, maxHp: c.maxHp, consBuys: [0, 0, 0, 0], consUse: [0, 0, 0, 0] }]));
  };
  const diffBody = (c, r) => {
    const o = B.get(c.index); if (!o) return;
    for (let i = 0; i < NITEM; ++i) {
      const d = c.items[i] - o.items[i];
      if (d) { o.buys.push([r, i, d]); if (i % 2 && d > 0) for (let k = 0; k < d; ++k) o.emb.push([r, i]); }
    }
    const dv0 = value(c.items) - value(o.items);
    if (dv0 > 0) o.spentItems += dv0;
    for (let i = 0; i < 4; ++i) {
      const d = c.cons[i] - o.cons[i];
      if (d > 0) { o.consBuys[i] += d; o.spentCons += 10 * d; }
      if (d < 0) o.consUse[i] += -d;
    }
    o.items = c.items.slice(); o.cons = c.cons.slice();
  };
  for (;;) {
    if (h.outcome || (h.awaiting && h.inPos >= size)) break;
    // state before the step = end of previous round when the next step opens a new round
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    const n = hdr();
    if (n.inPos === h.inPos && n.sub === h.sub) throw new Error('no progress');
    if (++guard > 6e6) throw new Error('runaway');
    if (n.phase !== 12) {
      if (n.round !== lastRound) {
        // read state at this step (first step of the new round); attribute to the previous round as the end-of-round state is
        // only exact before the step, so re-read previous via stored values: we record round-end values from the last read below.
        lastRound = n.round;
      }
      const isBuy = n.kind === 13 || n.kind === 15 || n.kind === 25 || n.kind === 20 || n.kind === 21;
      if (isBuy && n.akind === 1) {
        ensure();
        const cs = champs();
        const c = cs.find((x) => x.index === n.aidx);
        if (c) diffBody(c, n.round);
      }
    }
    // end-of-round snapshot: when the NEXT step changes round we cannot look ahead, so take a snapshot whenever round changes
    h = n;
    if (h.phase !== 12 && h.round !== endState?.round) {
      ensure();
      const cs = champs();
      // this state is after the first step of round h.round; for round-level stats (alive, maxHp, gold) that is close enough,
      // and we label it as the end of round h.round - 1.
      const r = h.round - 1;
      for (const c of cs) {
        const o = B.get(c.index); if (!o) continue;
        if (c.alive) o.aliveRounds += 1;
        if (o.alive && !c.alive) o.deaths.push([h.round, o.gems]);
        // catch item changes made outside shop steps (should not happen)
        let ch = false; for (let i = 0; i < NITEM; ++i) if (c.items[i] !== o.items[i]) { ch = true; break; }
        if (ch) { diffBody(c, h.round); o.offstep = (o.offstep || 0) + 1; }
        o.alive = c.alive; o.gems = c.gems; o.gold = c.gold; o.maxHp = c.maxHp;
        if (CPS.includes(r)) o.cp[r] = { maxHp: c.maxHp, alive: c.alive, gold: c.gold, gems: c.gems, spent: o.spentItems, spentC: o.spentCons, pts: pts(c.items), se: value(c.items) / 30 };
      }
      endState = { round: h.round };
    } else if (B && h.phase !== 12) {
      // deaths inside a round: track gems just before death using the actor's state at each step would be costly; approximate by
      // re-reading only on Death-like changes is not possible from the header, so bag at death comes from the dumps instead.
    }
  }
  ensure();
  const cs = champs();
  const final = h.round;
  for (const c of cs) {
    const o = B.get(c.index);
    o.cp.final = { r: final, maxHp: c.maxHp, alive: c.alive, gold: c.gold, gems: c.gems, spent: o.spentItems, spentC: o.spentCons, pts: pts(c.items), se: value(c.items) / 30 };
  }
  return { final, outcome: h.outcome, bodies, B };
}

const file = process.argv[2];
const name = path.basename(file);
try {
  const buf = unwrapReplay(fs.readFileSync(file));
  let res = null, err = null;
  for (const w of findEngineWasms()) { try { res = await run(w, buf); break; } catch (e) { err ??= e; } }
  if (!res) throw err || new Error('no engine');
  const bodies = res.bodies.map((b) => {
    const o = res.B.get(b.index);
    return { ...b, buys: o.buys, emb: o.emb, cp: o.cp, aliveRounds: o.aliveRounds, deaths: o.deaths, consBuys: o.consBuys, consUse: o.consUse, offstep: o.offstep || 0 };
  });
  console.log(JSON.stringify({ file: name, final: res.final, outcome: res.outcome, bodies }));
} catch (e) {
  console.log(JSON.stringify({ file: name, err: String(e.message || e) }));
}
