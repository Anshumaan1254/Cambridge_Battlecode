#!/usr/bin/env node
// Economy dump (an_economy): decode a replay once through the engine timeline (same path as tools/live/fightdump.mjs) and write a
// gzipped JSON with exact per-step gold / gem attribution and per-round camp health, for tools/top2/economy/econ_*.py:
//   meta  width, height, bodies [{index, team, type}], camps [{index, type, x, y, hp}], outcome (1 team 0 won, 2 team 1), finalRound, submitted
//   R     per round (end of round): [r, sub0, sub1, [[body, x, y, hp, maxHp, alive, gems, gold, stunned], ...]]
//   C     camp health changes at round ends: [r, camp, hp] (only when it differs from the previous round; round 0 = initial)
//   G     gold / gem changes inside one engine step: [q, r, body, dGold, dGems, stepKind, actorKind (1 champ, 2 camp, 0 engine), actorIndex]
//   D     deaths: [q, r, body, team, x, y, bag, killer (body, -1 camp, -2 other), stepKind]
//   S     stuns: [q, r, attacker (body, -1 camp), victim]
//   cd    champion damage on camps: [q, r, body, camp, amount]
//   dm    damage on champions: [q, r, attacker (body, -1 - camp), victim, amount, stepKind]
//   ev    champion actions (no Move / Set priority / Movement blocked): {q, r, k, who, to, slot}
// Usage: CAMBC_CACHE=... node tools/top2/economy/econ_dump.mjs OUTDIR replay   -> OUTDIR/<name>.json.gz, prints {"file": name, ok}
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, STEP, CHAMP, CAMP } from '../../replay/decode.mjs';

process.removeAllListeners('warning');
const CAMPN = [...CAMP, 'golem'];

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

function readTimeline(e, t) {
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true), f = (n) => e.getFloat32(t + n, true);
  const h = {
    round: u(8), phase: u(24), outcome: u(28), awaitingInput: !!u(20), inputPosition: u(56),
    submitted: [Number(e.getBigUint64(t + 32, true)), Number(e.getBigUint64(t + 40, true))],
    step: { kind: u(68), actor: { kind: u(72), index: u(76) }, from: { x: i(80), y: i(84) }, to: { x: i(88), y: i(92) }, round: u(96), substep: u(104), slot: u(108), abilityType: u(112) },
  };
  const table = (countOff, dataOff, stride, cap, fn) => {
    const n = u(countOff); if (n > cap) throw new Error('bad snapshot count');
    const r = new Array(n); for (let k = 0; k < n; ++k) r[k] = fn(dataOff + k * stride); return r;
  };
  h.champions = table(172, 196, 252, 16, (n) => ({
    index: u(n + 4), team: u(n + 8), type: u(n + 12), x: i(n + 16), y: i(n + 20), hp: f(n + 24), maxHp: f(n + 28), alive: !!u(n + 32),
    gold: u(n + 36), gems: u(n + 40), kills: u(n + 44), stunned: !!u(n + 248),
  }));
  h.camps = table(176, 4228, 28, 500, (n) => ({ index: u(n + 4), team: u(n + 8), type: u(n + 12), x: i(n + 16), y: i(n + 20), hp: f(n + 24) }));
  return h;
}

async function dump(wasmPath, buf) {
  const { X, out, dv, chk } = await loadEngine(wasmPath);
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load replay');
  const game = dv().getBigUint64(out, true);
  X.Engine_Free(p);
  if (X.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw new Error('unsupported timeline snapshot layout');
  const snap = X.Engine_Malloc(40152);
  const args = X.Engine_Malloc(128);
  chk(X.Game_GetBitboardMetadata(game, out), 'metadata');
  const width = dv().getInt32(out, true), height = dv().getInt32(out + 4, true);
  chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main timeline');
  const main = dv().getBigUint64(out, true);
  chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'timeline info');
  const size = dv().getUint32(args, true);
  chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');
  const read = () => { chk(X.Game_Visualiser_ReadTimelineState(game, snap), 'read'); return readTimeline(dv(), snap); };

  const R = [], C = [], G = [], D = [], S = [], cd = [], dm = [], ev = [];
  let prev = read(), meta = null, lastRound = -1, guard = 0, q = 0;
  const campLast = new Map();
  const compact = (s, r) => [r, s.submitted[0], s.submitted[1], s.champions.map((c) => [c.index, c.x, c.y, Math.round(c.hp), Math.round(c.maxHp), c.alive ? 1 : 0, c.gems, c.gold, c.stunned ? 1 : 0])];
  const campSnap = (s, r) => { for (const c of s.camps) { const h = Math.round(c.hp); if (campLast.get(c.index) !== h) { C.push([r, c.index, h]); campLast.set(c.index, h); } } };
  for (;;) {
    const s = prev;
    if (!meta && s.phase !== 12 && s.champions.length) {
      meta = {
        width, height,
        bodies: s.champions.map((c) => ({ index: c.index, team: c.team, type: CHAMP[c.type] ?? c.type })),
        camps: s.camps.map((c) => ({ index: c.index, type: CAMPN[c.type] ?? c.type, x: c.x, y: c.y, hp: c.hp })),
      };
      campSnap(s, 0);
    }
    if (s.outcome || (s.awaitingInput && s.inputPosition >= size)) break;
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    const n = read();
    if (n.inputPosition === s.inputPosition && n.step.substep === s.step.substep) throw new Error('timeline made no progress');
    if (++guard > 5e6) throw new Error('runaway replay');
    ++q;
    const st = n.step, r = st.round, kind = st.kind;
    const actorChamp = st.actor.kind === 1 ? st.actor.index : null;
    const actorCamp = st.actor.kind === 2 ? st.actor.index : null;
    if (n.phase !== 12 && actorChamp !== null && ![0, 3, 4, 7, 8, 9, 19, 23, 26].includes(kind)) {
      const e = { q, r, k: STEP[kind] || kind, who: actorChamp };
      if (st.to.x >= 0) e.to = [st.to.x, st.to.y];
      if (kind === 6) e.slot = st.slot;
      ev.push(e);
    }
    const pm = new Map(s.champions.map((c) => [c.index, c]));
    for (const c of n.champions) {
      const o = pm.get(c.index);
      if (!o) continue;
      const dg = c.gold - o.gold, dm2 = c.gems - o.gems;
      if (dg || dm2) G.push([q, r, c.index, dg, dm2, kind, st.actor.kind, st.actor.index]);
      if (o.alive) {
        const lost = o.hp - (c.alive ? c.hp : 0);
        if (lost > 0.5 && (actorChamp !== null || actorCamp !== null) && [1, 4, 5, 6, 21, 22].includes(kind)) {
          dm.push([q, r, actorChamp !== null ? actorChamp : -1 - actorCamp, c.index, Math.round(lost), kind]);
        }
        if (!o.stunned && c.stunned) S.push([q, r, actorChamp !== null ? actorChamp : -1, c.index]);
      }
      if (o.alive && !c.alive) D.push([q, r, c.index, c.team, o.x, o.y, o.gems, actorChamp !== null ? actorChamp : (actorCamp !== null ? -1 : -2), kind]);
    }
    if (actorChamp !== null && (kind === 5 || kind === 6)) {
      const cm = new Map(s.camps.map((c) => [c.index, c]));
      for (const c of n.camps) {
        const o = cm.get(c.index);
        if (o && o.hp - c.hp > 0.5) cd.push([q, r, actorChamp, c.index, Math.round(o.hp - c.hp)]);
      }
    }
    if (n.step.round !== lastRound && n.phase !== 12) {
      if (lastRound >= 0) { R.push(compact(s, lastRound)); campSnap(s, lastRound); }
      lastRound = n.step.round;
    }
    prev = n;
  }
  R.push(compact(prev, prev.step.round));
  campSnap(prev, prev.step.round);
  meta = meta || {};
  meta.outcome = prev.outcome;
  meta.finalRound = prev.step.round;
  meta.submitted = prev.submitted;
  return { meta, R, C, G, D, S, cd, dm, ev };
}

const [outdir, file] = process.argv.slice(2);
const name = path.basename(file);
const dst = path.join(outdir, name.replace(/\.repl26a$/, '.json.gz'));
try {
  if (fs.existsSync(dst)) { console.log(JSON.stringify({ file: name, ok: 1, cached: 1 })); process.exit(0); }
  const buf = unwrapReplay(fs.readFileSync(file));
  let res = null, err = null;
  for (const w of findEngineWasms()) {
    try { res = await dump(w, buf); break; } catch (e) { err ??= e; }
  }
  if (!res) throw err || new Error('no engine');
  res.meta.file = name;
  fs.writeFileSync(dst, zlib.gzipSync(JSON.stringify(res)));
  console.log(JSON.stringify({ file: name, ok: 1, rounds: res.meta.finalRound, G: res.G.length, C: res.C.length }));
} catch (e) {
  console.log(JSON.stringify({ file: name, ok: 0, err: String(e.message || e) }));
}
