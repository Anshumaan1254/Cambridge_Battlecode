#!/usr/bin/env node
// Per-map camp-group features (our half): groups, multi-attacker packs, elks, monoliths, gem groups.
//   node tools/replay/mapfeatures.mjs maps/*.map26a maps/ladder/*.map26a  -> JSON lines
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { findEngineWasms } from './decode.mjs';
process.removeAllListeners('warning');
const wasi = new WASI({ version: 'preview1', args: [], env: {} });
const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
wasi.initialize(inst);
const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
for (const file of process.argv.slice(2)) {
  if (path.basename(file).startsWith('zz_')) continue;
  const buf = fs.readFileSync(file);
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromMapFileBytes(p, buf.length, out, 0), 'load');
  const g = dv().getBigUint64(out, true);
  chk(X.Game_GetBitboardMetadata(g, out), 'meta');
  const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
  chk(X.Game_GetNumChampsPerTeam(g, out), 'n'); const champs = dv().getInt32(out, true);
  chk(X.Game_GetTeamASpawnArea(g, out), 'sp');
  const sx = (dv().getInt32(out, true) + dv().getInt32(out + 8, true)) / 2, sy = (dv().getInt32(out + 4, true) + dv().getInt32(out + 12, true)) / 2;
  chk(X.Game_GetNumCampGroups(g, out), 'ng'); const ng = dv().getUint32(out, true);
  const f = { map: path.basename(file, '.map26a'), w, h, champs, groups: 0, multi: 0, elk: 0, mono: 0, wolf: 0, gem: 0, gold: 0, packs: 0 };
  for (let i = 0; i < ng; i++) {
    chk(X.Game_GetCampGroupHandle(g, i, out), 'gh'); const gh = dv().getBigUint64(out, true);
    chk(X.Game_GetCampGroup(g, gh, out), 'grp'); const n = dv().getUint32(out + 12, true);
    let att = 0, cx = 0, cy = 0; const types = [];
    for (let k = 0; k < n; k++) {
      chk(X.Game_GetCampGroupCamp(g, gh, k, out), 'gc'); const ch = dv().getBigUint64(out, true);
      chk(X.Game_GetCamp(g, ch, out), 'c'); const t = dv().getInt32(out, true), x = dv().getInt32(out + 4, true), y = dv().getInt32(out + 8, true);
      types.push(t); cx += x; cy += y; if (t === 0 || t === 1 || t === 4) att++;
    }
    cx /= n; cy /= n;
    const mx = w - 1 - cx, my = h - 1 - cy; // rough: our half = closer to our spawn than the mirrored spawn
    const dOur = Math.hypot(cx - sx, cy - sy);
    const sym = (() => { chk(X.Game_GetSymmetry(g, out), 's'); return dv().getInt32(out, true); })();
    const esx = sym === 0 ? w - 1 - sx : sym === 1 ? sx : w - 1 - sx, esy = sym === 0 ? sy : sym === 1 ? h - 1 - sy : h - 1 - sy;
    if (dOur > Math.hypot(cx - esx, cy - esy)) continue;
    f.groups++; if (att >= 2) f.multi++; if (types.includes(1)) f.elk++; if (types.includes(4)) f.mono++; if (types.includes(0)) f.wolf++;
    if (types.includes(2)) f.gem++; if (types.includes(3) && att === 0 && !types.includes(2)) f.gold++;
    if (att >= 2 || (att >= 1 && n >= 3)) f.packs++;
  }
  console.log(JSON.stringify(f));
}
