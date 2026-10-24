#!/usr/bin/env node
// verify_economy dump (independent of tools/top2/economy): steps a replay through the engine timeline and records, per step,
// every champion gold / gem / alive change with the step kind and actor, camp alive<->dead transitions, group reward /
// captureTeam transitions and the actor of every Capture step. Positions per round come from the t2dump fight dumps.
// Usage: CAMBC_CACHE=... node tools/top2/verify_economy/vdump.mjs OUTDIR replay  -> OUTDIR/<name>.json.gz, prints a JSON line
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, STEP, CHAMP } from '../../replay/decode.mjs';
process.removeAllListeners('warning');

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

function snap(e, t) {
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true), f = (n) => e.getFloat32(t + n, true);
  const s = {
    round: u(8), phase: u(24), outcome: u(28), awaitingInput: !!u(20), inputPosition: u(56),
    submitted: [Number(e.getBigUint64(t + 32, true)), Number(e.getBigUint64(t + 40, true))],
    step: { kind: u(68), ak: u(72), ai: u(76), round: u(96), substep: u(104) },
  };
  const nc = u(172), nk = u(176), ng = u(180);
  if (nc > 16 || nk > 500 || ng > 500) throw new Error('bad snapshot count');
  s.ch = []; for (let k = 0; k < nc; ++k) { const n = 196 + k * 252; s.ch.push({ index: u(n + 4), team: u(n + 8), type: u(n + 12), x: i(n + 16), y: i(n + 20), alive: u(n + 32), gold: u(n + 36), gems: u(n + 40) }); }
  s.ca = []; for (let k = 0; k < nk; ++k) { const n = 4228 + k * 28; s.ca.push({ index: u(n + 4), g: u(n + 8), type: u(n + 12), x: i(n + 16), y: i(n + 20), hp: f(n + 24) }); }
  s.gr = []; for (let k = 0; k < ng; ++k) { const n = 18228 + k * 8; s.gr.push([u(n), u(n + 4)]); }
  return s;
}

async function run(wasmPath, buf) {
  const { X, out, dv, chk } = await loadEngine(wasmPath);
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load replay');
  const game = dv().getBigUint64(out, true);
  X.Engine_Free(p);
  if (X.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw new Error('unsupported timeline snapshot layout');
  const sp = X.Engine_Malloc(40152), args = X.Engine_Malloc(128);
  chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main timeline');
  const main = dv().getBigUint64(out, true);
  chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'timeline info');
  const size = dv().getUint32(args, true);
  chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');
  const read = () => { chk(X.Game_Visualiser_ReadTimelineState(game, sp), 'read'); return snap(dv(), sp); };
  const D = [], C = [], G = [], K = [];
  let prev = read(), meta = null, guard = 0, q = 0;
  for (;;) {
    const s = prev;
    if (!meta && s.phase !== 12 && s.ch.length) {
      meta = { bodies: s.ch.map((c) => [c.index, c.team, CHAMP[c.type] ?? c.type]), camps: s.ca.map((c) => [c.index, c.g, c.type, c.x, c.y, Math.round(c.hp)]), ngroups: s.gr.length };
    }
    if (s.outcome || (s.awaitingInput && s.inputPosition >= size)) break;
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    const n = read();
    if (n.inputPosition === s.inputPosition && n.step.substep === s.step.substep) throw new Error('timeline made no progress');
    if (++guard > 5e6) throw new Error('runaway replay');
    ++q;
    const st = n.step, r = st.round;
    if (n.phase === 12) { prev = n; continue; }
    if (st.kind === 2) K.push([q, r, st.ak, st.ai]);
    const pm = new Map(s.ch.map((c) => [c.index, c]));
    for (const c of n.ch) {
      const o = pm.get(c.index); if (!o) continue;
      if (o.gold !== c.gold || o.gems !== c.gems || o.alive !== c.alive) D.push([q, r, c.index, c.gold - o.gold, c.gems - o.gems, c.alive - o.alive, st.kind, st.ak, st.ai]);
    }
    for (let k = 0; k < n.ca.length && k < s.ca.length; ++k) {
      const a = s.ca[k].hp > 0 ? 1 : 0, b = n.ca[k].hp > 0 ? 1 : 0;
      if (a !== b) C.push([q, r, n.ca[k].index, b, st.kind]);
    }
    for (let k = 0; k < n.gr.length && k < s.gr.length; ++k) {
      if (n.gr[k][0] !== s.gr[k][0] || n.gr[k][1] !== s.gr[k][1]) G.push([q, r, k, n.gr[k][0], n.gr[k][1], st.kind, st.ak, st.ai]);
    }
    prev = n;
  }
  meta = meta || {};
  meta.outcome = prev.outcome; meta.finalRound = prev.step.round; meta.submitted = prev.submitted;
  return { meta, D, C, G, K };
}

const [outdir, file] = process.argv.slice(2);
const name = path.basename(file);
const dst = path.join(outdir, name.replace(/\.repl26a$/, '.json.gz'));
const t0 = Date.now();
try {
  const buf = unwrapReplay(fs.readFileSync(file));
  let res = null, err = null;
  for (const w of findEngineWasms()) { try { res = await run(w, buf); break; } catch (e) { err ??= e; } }
  if (!res) throw err || new Error('no engine');
  fs.writeFileSync(dst, zlib.gzipSync(JSON.stringify(res)));
  console.log(JSON.stringify({ file: name, ok: 1, rounds: res.meta.finalRound, ms: Date.now() - t0 }));
} catch (e) {
  console.log(JSON.stringify({ file: name, ok: 0, err: String(e.message || e) }));
}
