#!/usr/bin/env node
// Items dimension extractor: one pass over a replay (engine timeline, every step) -> one JSON line with, per body, every purchase
// (per-step item / consumable / gold diffs: shards by family x stat, emblems, crystals, altar locks), sells, gold earned / spent,
// checkpoints every 50 rounds (maxHp, hp, alive, gold, gems, kills, earned, spent), and per game the ward placements, altar-lock
// placements with context (enemy / own tribute channels at that altar, carriers nearby, later attacks on the lock), teleport
// crystals (walk distance saved, terrain crossed), tribute channels and stuns with the victim's channel state.
//   CAMBC_CACHE=... node tools/top2/items/ix.mjs replay.repl26a        (or through tools/live/par.py)
// Item ids follow the SDK enum: id = family*6 + stat*2 + emblem; families Monster Power Durability Treasure Jungle Home Bruiser,
// stats str foc hp. Consumable counters: cons[0] teleport crystal, cons[2] altar lock (probe.mjs).
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, STEP, CHAMP, CAMP } from '../../replay/decode.mjs';

process.removeAllListeners('warning');
const ITEM_COUNT = 42;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

async function loadEngine(wasmPath) {
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst);
  const X = inst.exports;
  const out = X.Engine_Malloc(64);
  const dv = () => new DataView(X.memory.buffer);
  const cstr = (p) => { const u = new Uint8Array(X.memory.buffer); let s = ''; while (u[p]) s += String.fromCharCode(u[p++]); return s; };
  const chk = (r, what) => { if (r !== 0) throw new Error(`${what}: engine code ${r}: ${cstr(X.GetLastErrorMsg())}`); };
  return { X, out, dv, chk };
}

function readSnap(e, t, full) {
  // full: also items + consumable counters (only Shop / Sell / lock / teleport / consumable steps change them) and camps
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true);
  const h = {
    round: u(8), phase: u(24), outcome: u(28), awaitingInput: !!u(20), inputPosition: u(56),
    submitted: [Number(e.getBigUint64(t + 32, true)), Number(e.getBigUint64(t + 40, true))],
    step: { kind: u(68), ak: u(72), ai: u(76), from: [i(80), i(84)], to: [i(88), i(92)], round: u(96), substep: u(104), slot: u(108) },
  };
  const n = u(172);
  if (n > 16) throw new Error('bad snapshot count');
  h.ch = new Array(n);
  for (let k = 0; k < n; ++k) {
    const b = t + 196 + k * 252;
    let items = null, cons = null;
    if (full) {
      items = new Array(ITEM_COUNT);
      for (let q = 0; q < ITEM_COUNT; ++q) items[q] = e.getUint32(b + 48 + q * 4, true);
      cons = [e.getUint32(b + 216, true), e.getUint32(b + 220, true), e.getUint32(b + 224, true), e.getUint32(b + 228, true)];
    }
    h.ch[k] = {
      index: e.getUint32(b + 4, true), team: e.getUint32(b + 8, true), type: e.getUint32(b + 12, true),
      x: e.getInt32(b + 16, true), y: e.getInt32(b + 20, true), hp: e.getFloat32(b + 24, true), maxHp: e.getFloat32(b + 28, true),
      alive: !!e.getUint32(b + 32, true), gold: e.getUint32(b + 36, true), gems: e.getUint32(b + 40, true), kills: e.getUint32(b + 44, true),
      items, cons, stunned: !!e.getUint32(b + 248, true),
    };
  }
  h.camps = [];
  if (full) {
    const nc = u(176);
    if (nc > 500) throw new Error('bad camp count');
    h.camps = new Array(nc);
    for (let k = 0; k < nc; ++k) { const b = t + 4228 + k * 28; h.camps[k] = { index: e.getUint32(b + 4, true), type: e.getUint32(b + 12, true), x: e.getInt32(b + 16, true), y: e.getInt32(b + 20, true), hp: e.getFloat32(b + 24, true) }; }
  }
  return h;
}

// shard equivalents per (family, stat): shards + 5 per emblem
function seOf(items) {
  const se = new Array(21).fill(0);
  for (let id = 0; id < ITEM_COUNT; ++id) if (items[id]) { const fs_ = Math.floor(id / 2); se[fs_] += items[id] * (id % 2 ? 5 : 1); }
  return se; // index = family*3 + stat
}

async function run(wasmPath, buf, name) {
  const { X, out, dv, chk } = await loadEngine(wasmPath);
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load replay');
  const game = dv().getBigUint64(out, true);
  X.Engine_Free(p);
  if (X.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw new Error('unsupported timeline snapshot layout');
  chk(X.Game_GetBitboardMetadata(game, out), 'metadata');
  const W = dv().getInt32(out, true), H = dv().getInt32(out + 4, true);
  // terrain
  const tile = (fn, x, y) => { chk(X[fn](game, x, y, out), fn); return dv().getUint8(out) !== 0; };
  const T = new Uint8Array(W * H); // 1 wall, 2 hole, 3 altar, bit 4 bush
  const altars = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let v = 0;
    if (tile('Game_GetWall', x, y)) v = 1; else if (tile('Game_GetHole', x, y)) v = 2; else if (tile('Game_GetAltar', x, y)) { v = 3; altars.push([x, y]); }
    if (tile('Game_GetBush', x, y)) v |= 4;
    T[y * W + x] = v;
  }
  const passable = (x, y) => x >= 0 && y >= 0 && x < W && y < H && (T[y * W + x] & 3) === 0;
  const bfs = (a, b, cap) => { // walking distance (8-neighbour) from a to b, -1 if > cap / unreachable
    if (!passable(b[0], b[1])) return -1;
    const D = new Int16Array(W * H).fill(-1); const Q = [a]; D[a[1] * W + a[0]] = 0;
    for (let h = 0; h < Q.length; h++) {
      const [x, y] = Q[h]; const d = D[y * W + x];
      if (x === b[0] && y === b[1]) return d;
      if (d >= cap) continue;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const nx = x + dx, ny = y + dy;
        if ((dx || dy) && passable(nx, ny) && D[ny * W + nx] < 0) { D[ny * W + nx] = d + 1; Q.push([nx, ny]); }
      }
    }
    return -1;
  };

  const snap = X.Engine_Malloc(40152);
  const args = X.Engine_Malloc(128);
  chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main timeline');
  const main = dv().getBigUint64(out, true);
  chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'timeline info');
  const size = dv().getUint32(args, true);
  chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');
  const read = (full) => { chk(X.Game_Visualiser_ReadTimelineState(game, snap), 'read'); return readSnap(dv(), snap, full); };
  const FULL = new Set([13, 15, 20, 21, 25]); // steps that change items / consumables
  const lastItems = {}, lastCons = {};

  let prev = read(true);
  let meta = null, guard = 0, lastRound = -1;
  const B = {}; // per body
  const team = {}, type = {};
  const spawnT = [[], []];
  let spawnC = [[0, 0], [0, 0]];
  const camps = [];
  const wards = [], locks = [], tele = [], tribs = [], stuns = [], lockAtt = [], subAtLocked = [];
  const trib = {}, rec = {}; // open channels
  const lockState = new Map(); // altar key -> {team, r, n, li}
  const near = (s, tm, pos, rad, enemy) => s.ch.filter((c) => c.alive && (enemy ? c.team !== tm : c.team === tm) && cheb([c.x, c.y], pos) <= rad);
  const dSpawn = (tm, pos) => Math.min(...spawnT[tm].map((q) => cheb(q, pos)));
  const nearestCamp = (pos) => { let b = 99; for (const c of camps) b = Math.min(b, cheb([c.x, c.y], pos)); return b; };
  const nearestAltar = (pos) => { let b = 99; for (const a of altars) b = Math.min(b, cheb(a, pos)); return b; };
  const closeTrib = (w, res, r) => { const t = trib[w]; if (!t) return; t.res = res; t.end = r; tribs.push(t); delete trib[w]; };

  for (;;) {
    const s = prev;
    if (!meta && s.phase !== 12 && s.ch.length) {
      meta = { W, H, bodies: s.ch.map((c) => ({ i: c.index, t: c.team, ty: CHAMP[c.type] ?? c.type })) };
      for (const c of s.ch) {
        team[c.index] = c.team; type[c.index] = CHAMP[c.type];
        spawnT[c.team].push([c.x, c.y]);
        B[c.index] = { i: c.index, t: c.team, ty: CHAMP[c.type], buys: [], sells: [], cp: {}, earned: 0, spent: 0, refund: 0, deaths: [], alive: 0 };
        lastItems[c.index] = c.items.slice(); lastCons[c.index] = c.cons.slice();
      }
      spawnC = spawnT.map((L) => [Math.round(L.reduce((a, q) => a + q[0], 0) / L.length), Math.round(L.reduce((a, q) => a + q[1], 0) / L.length)]);
      for (const c of s.camps) camps.push({ x: c.x, y: c.y, type: CAMP[c.type] ?? c.type });
    }
    if (s.outcome || (s.awaitingInput && s.inputPosition >= size)) break;
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    let n = read(!meta);
    if (meta && FULL.has(n.step.kind)) n = read(true);
    if (n.inputPosition === s.inputPosition && n.step.substep === s.step.substep) throw new Error('timeline made no progress');
    if (++guard > 5e6) throw new Error('runaway replay');
    const st = n.step, r = st.round, kind = st.kind;
    const actor = st.ak === 1 ? st.ai : null;
    if (meta && n.phase !== 12) {
      const pm = new Map(s.ch.map((c) => [c.index, c]));
      for (const c of n.ch) {
        const o = pm.get(c.index);
        if (!o || !B[c.index]) continue;
        const b = B[c.index];
        // gold
        const dg = c.gold - o.gold;
        if (dg > 0 && kind !== 25) b.earned += dg;
        if (dg > 0 && kind === 25) b.refund += dg;
        if (dg < 0 && kind === 13) b.spent += -dg;
        // items / consumables (read only on the steps that change them)
        if (c.items) {
          const oi = lastItems[c.index], oc = lastCons[c.index];
          let changed = false;
          for (let id = 0; id < ITEM_COUNT; ++id) if (c.items[id] !== oi[id]) { changed = true; break; }
          const state = !o.alive ? 0 : (spawnT[c.team].some((q) => q[0] === o.x && q[1] === o.y) ? 1 : 2);
          if (changed) {
            const s0 = seOf(oi), s1 = seOf(c.items);
            for (let k = 0; k < 21; ++k) {
              const d = s1[k] - s0[k];
              if (d > 0) b.buys.push([r, k, d, o.gold, state]);
              else if (d < 0) b.sells.push([r, k, -d, kind]);
            }
          }
          for (let k = 0; k < 4; ++k) {
            const d = c.cons[k] - oc[k];
            if (d > 0) b.buys.push([r, 100 + k, d, o.gold, state]);
          }
          lastItems[c.index] = c.items; lastCons[c.index] = c.cons;
        }
        // stuns (flag rises) with the victim's channel state
        if (o.alive && !o.stunned && c.stunned) {
          const t = trib[c.index], rc = rec[c.index];
          stuns.push([r, actor ?? -1, c.index, kind === 6 ? st.slot : -1, t ? t.bag : -1, t ? r - t.r : -1, rc ? r - rc.r : -1, rc ? rc.n : 0, Math.round(100 * o.hp / Math.max(1, o.maxHp)), o.gems]);
          if (t) closeTrib(c.index, 'stun', r);
          if (rc) delete rec[c.index];
        }
        // damage cancels a recall
        if (o.alive && c.hp < o.hp - 0.5 && rec[c.index]) delete rec[c.index];
        if (o.alive && !c.alive) {
          b.deaths.push([r, o.gems, actor ?? (st.ak === 2 ? 'camp' : st.ak)]);
          closeTrib(c.index, 'death', r);
          delete rec[c.index];
        }
        // recall arrival: jump onto own spawn
        if (rec[c.index] && c.alive && cheb([o.x, o.y], [c.x, c.y]) > 2 && spawnT[c.team].some((q) => q[0] === c.x && q[1] === c.y)) delete rec[c.index];
      }
      if (actor !== null && B[actor]) {
        const me = n.ch.find((c) => c.index === actor);
        const my = s.ch.find((c) => c.index === actor);
        const tm = team[actor];
        const pos = my ? [my.x, my.y] : [0, 0];
        if (kind === 14) { // ward
          const to = st.to;
          const en = near(s, tm, pos, 8, true);
          wards.push([r, actor, to[0], to[1], (T[to[1] * W + to[0]] & 4) ? 1 : 0, nearestCamp(to), nearestAltar(to), dSpawn(tm, to), dSpawn(1 - tm, to), cheb(pos, to), en.length ? Math.min(...en.map((c) => cheb([c.x, c.y], pos))) : 99, (T[pos[1] * W + pos[0]] & 4) ? 1 : 0]);
        } else if (kind === 20) { // altar lock
          const a = st.to;
          const enemyTrib = Object.entries(trib).filter(([w, t]) => team[w] !== tm && cheb(t.altar, a) === 0).map(([w, t]) => [+w, t.bag, r - t.r]);
          const ownTrib = Object.entries(trib).filter(([w, t]) => team[w] === tm && cheb(t.altar, a) <= 0).map(([w, t]) => [+w, t.bag]);
          const en8 = near(s, tm, a, 8, true), al8 = near(s, tm, a, 8, false);
          const carriers = en8.filter((c) => c.gems > 0);
          const li = locks.length;
          locks.push({
            r, who: actor, t: tm, a, enemyTrib, ownTrib, en8: en8.length, al8: al8.length, enBag8: carriers.reduce((x, c) => x + c.gems, 0),
            enMaxBag8: carriers.length ? Math.max(...carriers.map((c) => c.gems)) : 0,
            enCarrierD: carriers.length ? Math.min(...carriers.map((c) => cheb([c.x, c.y], a))) : 99,
            myBag: my ? my.gems : 0, myD: cheb(pos, a), aOwn: dSpawn(tm, a), aEnemy: dSpawn(1 - tm, a),
            att: 0, cleared: -1, enSubs: 0, ownBanks: 0, ownBankGems: 0,
          });
          for (const [w] of enemyTrib) closeTrib(w, 'lock', r);
          lockState.set(a[0] + ',' + a[1], { team: tm, r, li });
        } else if (kind === 21) { // teleport channel start
          const to = st.to;
          const en = near(s, tm, pos, 6, true);
          tele.push({ r, who: actor, from: pos, to, walk: bfs(pos, to, 80), cheb: cheb(pos, to), en6: en.length, bag: my ? my.gems : 0, hpf: my ? Math.round(100 * my.hp / Math.max(1, my.maxHp)) : 0, campD: nearestCamp(to), altarD: nearestAltar(to), dOwn: dSpawn(tm, pos), dOwnTo: dSpawn(tm, to), done: 0 });
        } else if (kind === 22) {
          for (let k = tele.length - 1; k >= 0; --k) if (tele[k].who === actor && !tele[k].done) { tele[k].done = r; break; }
        } else if (kind === 12) { // tribute start
          const a = st.to[0] >= 0 ? st.to : pos;
          const key = a[0] + ',' + a[1];
          const L = lockState.get(key);
          if (L && L.team !== tm && locks[L.li].cleared < 0) { locks[L.li].enSubs++; subAtLocked.push([r, actor, a[0], a[1], my ? my.gems : 0]); }
          if (trib[actor]) closeTrib(actor, 'restart', r);
          trib[actor] = { r, who: actor, t: tm, altar: a, bag: my ? my.gems : 0, en6: near(s, tm, pos, 6, true).length };
        } else if (kind === 18) { // gems submitted
          const t = trib[actor];
          const got = my && me ? my.gems - me.gems : 0;
          if (t) { t.gems = got; closeTrib(actor, 'ok', r); }
          const L = t ? lockState.get(t.altar[0] + ',' + t.altar[1]) : null;
          if (L && L.team === tm && locks[L.li].cleared < 0) { locks[L.li].ownBanks++; locks[L.li].ownBankGems += got; }
        } else if (kind === 16) { // cancel channel
          if (trib[actor]) closeTrib(actor, 'cancel', r);
          else delete rec[actor];
        } else if (kind === 11) { // recall start
          rec[actor] = { r, n: (rec[actor]?.n || 0) + 1 };
        } else if (kind === 5) { // attack: on a locked altar tile?
          const to = st.to;
          if (to[0] >= 0 && to[1] >= 0 && to[0] < W && to[1] < H && (T[to[1] * W + to[0]] & 3) === 3) {
            const key = to[0] + ',' + to[1];
            const L = lockState.get(key);
            lockAtt.push([r, actor, to[0], to[1], L ? (L.team === tm ? 'own' : 'enemy') : 'none']);
            if (L && L.team !== tm && locks[L.li].cleared < 0) {
              const lk = locks[L.li];
              lk.att++;
              if (lk.att >= 5) { lk.cleared = r; lockState.delete(key); }
            }
          }
        }
      }
    }
    if (n.phase !== 12 && st.round !== lastRound) {
      // end of round lastRound = state s
      if (meta && lastRound >= 0) {
        for (const c of s.ch) {
          const b = B[c.index]; if (!b) continue;
          if (c.alive) b.alive++;
          if (lastRound % 50 === 0) b.cp[lastRound] = [Math.round(c.maxHp), Math.round(c.hp), c.alive ? 1 : 0, c.gold, c.gems, c.kills, b.earned, b.spent];
        }
      }
      lastRound = st.round;
    }
    prev = n;
  }
  const fin = prev;
  for (const c of fin.ch) {
    if (!c.items) c.items = lastItems[c.index];
    const b = B[c.index]; if (!b) continue;
    b.fin = [Math.round(c.maxHp), Math.round(c.hp), c.alive ? 1 : 0, c.gold, c.gems, c.kills, b.earned, b.spent];
    b.items = []; for (let id = 0; id < ITEM_COUNT; ++id) if (c.items[id]) b.items.push([id, c.items[id]]);
  }
  for (const w of Object.keys(trib)) closeTrib(+w, 'open', fin.step.round);
  return {
    file: name, W, H, outcome: fin.outcome, final: fin.step.round, sub: fin.submitted, bodies: meta.bodies, spawnC, nAltars: altars.length,
    altars, B: Object.values(B), wards, locks, tele, tribs: tribs.map((t) => [t.r, t.who, t.altar[0], t.altar[1], t.bag, t.res, t.end, t.gems ?? 0, t.en6]),
    stuns, lockAtt, subAtLocked,
  };
}

const file = process.argv[2];
const name = path.basename(file);
try {
  const buf = unwrapReplay(fs.readFileSync(file));
  let res = null, err = null;
  for (const w of findEngineWasms()) {
    try { res = await run(w, buf, name); break; } catch (e) { err ??= e; }
  }
  if (!res) throw err || new Error('no engine');
  console.log(JSON.stringify(res));
} catch (e) {
  console.error(JSON.stringify({ file: name, ok: 0, err: String(e.message || e) }));
}
