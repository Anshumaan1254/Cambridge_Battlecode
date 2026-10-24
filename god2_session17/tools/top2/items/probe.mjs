#!/usr/bin/env node
// Probe (items dimension): print raw step fields of Shop / consumable / lock / teleport / ward steps and the 4 per-champion
// consumable counters around them, to learn which counter is which.   CAMBC_CACHE=... node tools/top2/items/probe.mjs replay
import fs from 'node:fs';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay, STEP, CHAMP } from '../../replay/decode.mjs';

process.removeAllListeners('warning');
const ITEM_COUNT = 42;
const file = process.argv[2];
const buf = unwrapReplay(fs.readFileSync(file));
const wasm = findEngineWasms()[0];
const wasi = new WASI({ version: 'preview1', args: [], env: {} });
const mod = await WebAssembly.compile(fs.readFileSync(wasm));
const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
wasi.initialize(inst);
const X = inst.exports;
const out = X.Engine_Malloc(64);
const dv = () => new DataView(X.memory.buffer);
const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
const p = X.Engine_Malloc(buf.length);
new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load');
const game = dv().getBigUint64(out, true);
const snap = X.Engine_Malloc(40152);
const args = X.Engine_Malloc(128);
chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main');
const main = dv().getBigUint64(out, true);
chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'info');
const size = dv().getUint32(args, true);
chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');
function read() {
  chk(X.Game_Visualiser_ReadTimelineState(game, snap), 'read');
  const e = dv(), t = snap;
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true), f = (n) => e.getFloat32(t + n, true);
  const h = { round: u(8), phase: u(24), outcome: u(28), awaitingInput: !!u(20), inputPosition: u(56) };
  h.step = { kind: u(68), ak: u(72), ai: u(76), fx: i(80), fy: i(84), tx: i(88), ty: i(92), round: u(96), sub: u(104), slot: u(108), at: u(112), pr: i(116), raw: [] };
  for (let k = 64; k < 172; k += 4) h.step.raw.push(i(k));
  const n = u(172);
  h.ch = [];
  for (let k = 0; k < n; ++k) {
    const b = 196 + k * 252;
    const items = []; for (let q = 0; q < ITEM_COUNT; ++q) { const c = u(b + 48 + q * 4); if (c) items.push([q, c]); }
    const tail = []; for (let q = 216; q < 252; q += 4) tail.push(u(b + q));
    h.ch.push({ idx: u(b + 4), team: u(b + 8), type: u(b + 12), gold: u(b + 36), items, tail });
  }
  return h;
}
let prev = read(), guard = 0, shown = 0;
for (;;) {
  if (prev.outcome || (prev.awaitingInput && prev.inputPosition >= size)) break;
  X.Game_Visualiser_Timeline_ReplayNext(game, 1);
  const n = read();
  if (++guard > 5e6) break;
  const k = STEP[n.step.kind];
  if (['Shop', 'Consumable', 'Place altar lock', 'Teleport channel', 'Teleport complete', 'Sell item', 'Place ward'].includes(k) && shown < 100000) {
    const c0 = prev.ch.find((c) => c.idx === n.step.ai), c1 = n.ch.find((c) => c.idx === n.step.ai);
    console.log(n.step.round, k, 'who', n.step.ai, CHAMP[c1?.type], 'step', JSON.stringify(n.step.raw.slice(0, 16)),
      'gold', c0?.gold, '->', c1?.gold, 'items', JSON.stringify(c0?.items), '->', JSON.stringify(c1?.items), 'tail', JSON.stringify(c0?.tail), '->', JSON.stringify(c1?.tail));
    ++shown;
  }
  prev = n;
}
