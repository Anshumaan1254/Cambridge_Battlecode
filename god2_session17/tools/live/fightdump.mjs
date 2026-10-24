#!/usr/bin/env node
// Fight dump: decode a replay once (same engine path as tools/replay/decode.mjs) and write a compact gzipped JSON with what fight
// analyses need, with EXACT per-step attribution from the timeline (health diffs inside the step of the acting champion / camp):
//   dmg   [q, r, attacker body (-1 - campIndex for a camp), victim body, amount, kind 5 attack / 6 cast, slot]   (a == v: Ren reflect)
//   cdmg  [q, r, attacker body, camp index, amount]       champion damage on camps
//   stun  [q, r, attacker body (-1 camp), victim body]
//   heal  [q, r, caster body, target body, amount]        (casts only; spawn healing is not an event)
//   R     per round (end of round): [r, sub0, sub1, [[body, x, y, hp, maxHp, alive, gems, gold, kills, stunned], ...]]
//   ev    action events (moves, attacks, casts, recalls, submits, shop, wards, consumables, channels) + Death / CaptureGems / Banked,
//         each with q = step sequence number (orders actions inside a round)
//   meta  width, height, bodies, camps, outcome, finalRound, submitted
// Usage: CAMBC_CACHE=... node tools/live/fightdump.mjs OUTDIR replay   -> OUTDIR/<name>.json.gz, prints {"file": name, ...}
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, STEP, CHAMP, CAMP } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const ITEM_COUNT = 42;

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

  const R = [], ev = [], dmg = [], cdmg = [], stun = [], heal = [];
  let prev = read(), meta = null, lastRound = -1, guard = 0, q = 0;
  const compact = (s, r) => [r, s.submitted[0], s.submitted[1], s.champions.map((c) => [c.index, c.x, c.y, Math.round(c.hp), Math.round(c.maxHp), c.alive ? 1 : 0, c.gems, c.gold, c.kills, c.stunned ? 1 : 0])];
  for (;;) {
    const s = prev;
    if (!meta && s.phase !== 12 && s.champions.length) {
      meta = {
        width, height,
        bodies: s.champions.map((c) => ({ index: c.index, team: c.team, type: CHAMP[c.type] ?? c.type })),
        camps: s.camps.map((c) => ({ index: c.index, type: CAMP[c.type] ?? c.type, x: c.x, y: c.y, hp: c.hp })),
      };
    }
    if (s.outcome || (s.awaitingInput && s.inputPosition >= size)) break;
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    const n = read();
    if (n.inputPosition === s.inputPosition && n.step.substep === s.step.substep) throw new Error('timeline made no progress');
    if (++guard > 5e6) throw new Error('runaway replay');
    ++q;
    const st = n.step, r = st.round;
    const actorChamp = st.actor.kind === 1 ? st.actor.index : null;
    const actorCamp = st.actor.kind === 2 ? st.actor.index : null;
    if (n.phase !== 12 && st.kind !== 0 && st.kind !== 3 && st.kind !== 7 && st.kind !== 8 && st.kind !== 9 && st.kind !== 26 && st.kind !== 23 && st.kind !== 19) {
      const e = { q, r, k: STEP[st.kind] || st.kind };
      if (actorChamp !== null) e.who = actorChamp;
      else if (actorCamp !== null) e.camp = actorCamp;
      if (st.from.x >= 0) e.from = [st.from.x, st.from.y];
      if (st.to.x >= 0) e.to = [st.to.x, st.to.y];
      if (st.kind === 6) { e.slot = st.slot; e.ability = st.abilityType; }
      // camp attacks are frequent and carried by dmg[]; keep only champion actions here
      if (actorCamp === null) ev.push(e);
    }
    const pm = new Map(s.champions.map((c) => [c.index, c]));
    const actorTeam = actorChamp !== null ? (pm.get(actorChamp)?.team) : null;
    for (const c of n.champions) {
      const o = pm.get(c.index);
      if (!o) continue;
      if (o.alive) {
        const lost = o.hp - (c.alive ? c.hp : 0);
        if (lost > 0.5 && (actorChamp !== null || actorCamp !== null) && (st.kind === 5 || st.kind === 6 || st.kind === 1 || st.kind === 4 || st.kind === 21 || st.kind === 22)) {
          const a = actorChamp !== null ? actorChamp : -1 - actorCamp;
          dmg.push([q, r, a, c.index, Math.round(lost), st.kind, st.kind === 6 ? st.slot : -1]);
        } else if (lost < -0.5 && actorChamp !== null && st.kind === 6 && c.alive) {
          heal.push([q, r, actorChamp, c.index, Math.round(-lost)]);
        }
        if (!o.stunned && c.stunned) stun.push([q, r, actorChamp !== null ? actorChamp : -1, c.index]);
      }
      if (o.alive && !c.alive) ev.push({ q, r, k: 'Death', who: c.index, team: c.team, at: [o.x, o.y], bag: o.gems, by: actorChamp !== null ? actorChamp : (actorCamp !== null ? 'camp' : st.actor.kind), step: STEP[st.kind] });
      if (c.gems > o.gems && st.kind === 2) ev.push({ q, r, k: 'CaptureGems', who: c.index, team: c.team, gems: c.gems - o.gems, gold: c.gold - o.gold, at: [c.x, c.y] });
      if (c.gems < o.gems && c.alive && st.kind === 18) ev.push({ q, r, k: 'Banked', who: c.index, team: c.team, gems: o.gems - c.gems, at: [c.x, c.y] });
    }
    if (actorChamp !== null && (st.kind === 5 || st.kind === 6)) {
      const cm = new Map(s.camps.map((c) => [c.index, c]));
      for (const c of n.camps) {
        const o = cm.get(c.index);
        if (o && o.hp - c.hp > 0.5) cdmg.push([q, r, actorChamp, c.index, Math.round(o.hp - c.hp)]);
      }
    }
    if (n.step.round !== lastRound && n.phase !== 12) {
      if (lastRound >= 0) R.push(compact(s, lastRound));
      lastRound = n.step.round;
    }
    prev = n;
  }
  R.push(compact(prev, prev.step.round));
  meta = meta || {};
  meta.outcome = prev.outcome;
  meta.finalRound = prev.step.round;
  meta.submitted = prev.submitted;
  return { meta, R, ev, dmg, cdmg, stun, heal };
}

const [outdir, file] = process.argv.slice(2);
const name = path.basename(file);
const dst = path.join(outdir, name.replace(/\.repl26a$/, '.json.gz'));
try {
  let buf = unwrapReplay(fs.readFileSync(file));
  let res = null, err = null;
  for (const w of findEngineWasms()) {
    try { res = await dump(w, buf); break; } catch (e) { err ??= e; }
  }
  if (!res) throw err || new Error('no engine');
  fs.writeFileSync(dst, zlib.gzipSync(JSON.stringify(res)));
  console.log(JSON.stringify({ file: name, ok: 1, rounds: res.meta.finalRound, dmg: res.dmg.length }));
} catch (e) {
  console.log(JSON.stringify({ file: name, ok: 0, err: String(e.message || e) }));
}
