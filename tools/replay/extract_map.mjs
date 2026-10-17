#!/usr/bin/env node
// Rebuild the .map26a a replay was played on (ladder / scrim maps), so we can run local games on it.
//
//   node tools/replay/extract_map.mjs replay.repl26a out.map26a
//   node tools/replay/extract_map.mjs --dir <folder with replays> <out maps dir> [prefix]
//
// Reads terrain, altars, camps, spawn area, symmetry and team size through the engine's Game_* exports
// and re-encodes them with its MapBuilder (which mirrors everything for the other team).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay } from './decode.mjs';

process.removeAllListeners('warning');

async function load(wasmPath) {
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

export async function extractMap(buf) {
  buf = unwrapReplay(buf);
  let lastErr;
  for (const w of findEngineWasms()) {
    try { return await extractWith(w, buf); } catch (e) { lastErr = e; }
  }
  throw lastErr;
}

async function extractWith(wasmPath, buf) {
  const { X, out, dv, chk } = await load(wasmPath);
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load replay');
  const g = dv().getBigUint64(out, true);
  const i32 = (fn, ...a) => { chk(X[fn](g, ...a, out), fn); return dv().getInt32(out, true); };
  chk(X.Game_GetBitboardMetadata(g, out), 'meta');
  const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
  const sym = i32('Game_GetSymmetry');
  const champs = i32('Game_GetNumChampsPerTeam');
  chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
  const spawn = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
  const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return dv().getUint8(out) !== 0; };
  const nc = (() => { chk(X.Game_GetNumCamps(g, out), 'ncamps'); return dv().getUint32(out, true); })();
  const camps = [];
  for (let i = 0; i < nc; i++) {
    chk(X.Game_GetCampHandle(g, i, out), 'camp handle');
    const hnd = dv().getBigUint64(out, true);
    chk(X.Game_GetCamp(g, hnd, out), 'camp');
    camps.push([dv().getInt32(out, true), dv().getInt32(out + 4, true), dv().getInt32(out + 8, true)]);
  }
  // Re-encode
  chk(X.MapBuilder_Create(w, h, sym, out), 'create');
  const b = dv().getBigUint64(out, true);
  const call = (fn, ...a) => chk(X[fn](b, ...a), fn);
  call('MapBuilder_SetNumChampsPerTeam', champs);
  dv().setInt32(out, spawn[0], true); dv().setInt32(out + 4, spawn[1], true); dv().setInt32(out + 8, spawn[2], true); dv().setInt32(out + 12, spawn[3], true);
  chk(X.MapBuilder_SetTeamASpawnArea(b, out), 'spawn');
  const stats = { walls: 0, bushes: 0, holes: 0, altars: 0, camps: 0 };
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (tile('Game_GetWall', x, y)) { try { call('MapBuilder_AddWall', x, y); stats.walls++; } catch {} }
    else if (tile('Game_GetHole', x, y)) { try { call('MapBuilder_AddHole', x, y); stats.holes++; } catch {} }
    else if (tile('Game_GetAltar', x, y)) { try { call('MapBuilder_AddAltar', x, y); stats.altars++; } catch {} }
    if (tile('Game_GetBush', x, y)) { try { call('MapBuilder_AddBush', x, y); stats.bushes++; } catch {} }
  }
  for (const [t, x, y] of camps) {
    // The builder mirrors camps; the mirrored copy of an earlier camp already occupies this tile.
    chk(X.MapBuilder_GetCampHandle ? 0 : 0, 'noop');
    try { chk(X.MapBuilder_AddCamp(b, t, x, y, out), 'camp'); stats.camps++; } catch {}
  }
  chk(X.MapBuilder_VerifyIntegrity(b), 'verify');
  chk(X.MapBuilder_Encode(b, out, out + 4), 'encode');
  const ptr = dv().getUint32(out, true), n = dv().getUint32(out + 4, true);
  const bytes = new Uint8Array(X.memory.buffer, ptr, n).slice();
  chk(X.MapBuilder_GetNumCamps(b, out), 'n');
  stats.campsTotal = dv().getUint32(out, true);
  stats.campsInReplay = nc;
  return { bytes, info: { w, h, sym: ['H', 'V', 'R'][sym] ?? sym, champs, spawn, ...stats } };
}

const argv = process.argv.slice(2);
if (argv[0] === '--dir') {
  const [, dir, outDir, prefix = 'lad_'] = argv;
  fs.mkdirSync(outDir, { recursive: true });
  const files = [];
  const walk = (d) => { for (const f of fs.readdirSync(d)) { const p = path.join(d, f); if (fs.statSync(p).isDirectory()) walk(p); else if (f.endsWith('.repl26a')) files.push(p); } };
  walk(dir);
  const seen = new Map();
  for (const f of files.sort()) {
    try {
      const { bytes, info } = await extractMap(fs.readFileSync(f));
      const hash = crypto.createHash('sha1').update(bytes).digest('hex').slice(0, 6);
      if (seen.has(hash)) { console.log(`${f} -> same map as ${seen.get(hash)}`); continue; }
      const name = `${prefix}${info.w}x${info.h}_${info.sym}_c${info.champs}_${hash}`;
      fs.writeFileSync(path.join(outDir, name + '.map26a'), bytes);
      seen.set(hash, name);
      console.log(`${f} -> ${name} ${JSON.stringify(info)}`);
    } catch (e) { console.log(`${f}: FAILED ${e.message}`); }
  }
} else {
  const [inp, outp] = argv;
  if (!inp || !outp) { console.error('usage: extract_map.mjs replay.repl26a out.map26a | --dir DIR OUTDIR [prefix]'); process.exit(2); }
  const { bytes, info } = await extractMap(fs.readFileSync(inp));
  fs.writeFileSync(outp, bytes);
  console.log(JSON.stringify(info));
}
