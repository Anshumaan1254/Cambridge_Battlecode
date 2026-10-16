#!/usr/bin/env node
// ASCII view of a map (.map26a) or of the map inside a replay: walls #, holes o, bushes ", altars A,
// spawn S (team A) / s (team B), camps W wolf E elk g gem $ gold M monolith.
//   node tools/replay/mapinfo.mjs maps/ladder/x.map26a
import fs from 'node:fs';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay } from './decode.mjs';
process.removeAllListeners('warning');
const file = process.argv[2];
let buf = fs.readFileSync(file);
const isReplay = file.endsWith('.repl26a');
if (isReplay) buf = unwrapReplay(buf);
const wasi = new WASI({ version: 'preview1', args: [], env: {} });
const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
wasi.initialize(inst);
const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
const p = X.Engine_Malloc(buf.length);
new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
chk(isReplay ? X.Game_FromReplayFileBytes(p, buf.length, out) : X.Game_FromMapFileBytes(p, buf.length, out, 0), 'load');
const g = dv().getBigUint64(out, true);
chk(X.Game_GetBitboardMetadata(g, out), 'meta');
const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
chk(X.Game_GetSymmetry(g, out), 'sym'); const sym = dv().getInt32(out, true);
chk(X.Game_GetNumChampsPerTeam(g, out), 'n'); const champs = dv().getInt32(out, true);
chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
const sp = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return dv().getUint8(out) !== 0; };
const grid = Array.from({ length: h }, () => Array(w).fill('.'));
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
  if (tile('Game_GetWall', x, y)) grid[y][x] = '#';
  else if (tile('Game_GetHole', x, y)) grid[y][x] = 'o';
  else if (tile('Game_GetAltar', x, y)) grid[y][x] = 'A';
  else if (tile('Game_GetBush', x, y)) grid[y][x] = '"';
}
const mirror = (x, y) => sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y];
for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) {
  if (y < h && x < w) { grid[y][x] = 'S'; const [mx, my] = mirror(x, y); grid[my][mx] = 's'; }
}
chk(X.Game_GetNumCamps(g, out), 'nc'); const nc = dv().getUint32(out, true);
const sym2 = ['W', 'E', 'g', '$', 'M'];
const counts = {};
for (let i = 0; i < nc; i++) {
  chk(X.Game_GetCampHandle(g, i, out), 'ch'); const hnd = dv().getBigUint64(out, true);
  chk(X.Game_GetCamp(g, hnd, out), 'camp');
  const t = dv().getInt32(out, true), x = dv().getInt32(out + 4, true), y = dv().getInt32(out + 8, true);
  grid[y][x] = sym2[t] ?? '?'; counts[sym2[t]] = (counts[sym2[t]] || 0) + 1;
  const [mx, my] = mirror(x, y); grid[my][mx] = sym2[t] ?? '?';
}
console.log(`${file}: ${w}x${h} sym ${['H(x mirrored)', 'V(y mirrored)', 'R180'][sym]} champs ${champs} spawnA ${sp} camps(per side) ${JSON.stringify(counts)}`);
for (let y = 0; y < h; y++) console.log(String(y).padStart(3) + ' ' + grid[y].join(''));
