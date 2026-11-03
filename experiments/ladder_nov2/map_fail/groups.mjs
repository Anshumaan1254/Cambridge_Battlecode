#!/usr/bin/env node
// Camp groups of the map inside a replay (engine wasm API): one JSON line per replay
//   {mid, ngroups, groups: [{g, camps: [[type, x, y], ...]}]}   type: 0 wolf 1 elk 2 gem 3 gold 4 monolith
//   node map_fail/groups.mjs replays/<id>.repl26a ...
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay } from '../../../tools/replay/decode.mjs';
process.removeAllListeners('warning');
const wasi = new WASI({ version: 'preview1', args: [], env: {} });
const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
wasi.initialize(inst);
const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
for (const file of process.argv.slice(2)) {
  let buf = unwrapReplay(fs.readFileSync(file));
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load');
  const g = dv().getBigUint64(out, true);
  chk(X.Game_GetNumCampGroups(g, out), 'ng'); const ng = dv().getUint32(out, true);
  const groups = [];
  for (let i = 0; i < ng; i++) {
    chk(X.Game_GetCampGroupHandle(g, i, out), 'gh'); const gh = dv().getBigUint64(out, true);
    chk(X.Game_GetCampGroup(g, gh, out), 'grp');
    const raw = [0, 4, 8, 12, 16, 20, 24, 28].map((o) => dv().getInt32(out + o, true));
    const n = dv().getUint32(out + 12, true);
    const camps = [];
    for (let k = 0; k < n; k++) {
      chk(X.Game_GetCampGroupCamp(g, gh, k, out), 'gc'); const ch = dv().getBigUint64(out, true);
      chk(X.Game_GetCamp(g, ch, out), 'c');
      camps.push([dv().getInt32(out, true), dv().getInt32(out + 4, true), dv().getInt32(out + 8, true)]);
    }
    groups.push({ g: i, raw, camps });
  }
  console.log(JSON.stringify({ mid: path.basename(file, '.repl26a'), ngroups: ng, groups }));
}
