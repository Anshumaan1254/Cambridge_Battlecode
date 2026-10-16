// Thin Node wrapper over the engine's MapBuilder_* exports (same wasm the map editor ships).
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
process.removeAllListeners('warning');

// The map editor ships the engine as wasm inside the cambc asset cache; use the newest copy found there.
export function findEngineWasm() {
  const local = path.join(here, 'engine.wasm');
  if (fs.existsSync(local)) return local;
  const home = process.env.HOME || '/root';
  const roots = [process.env.CAMBC_CACHE, path.join(home, '.cache', 'cambc', 'assets')].filter(Boolean);
  const found = [];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    for (const hash of fs.readdirSync(root)) {
      const dir = path.join(root, hash, 'mapeditor', 'assets');
      if (!fs.existsSync(dir)) continue;
      for (const f of fs.readdirSync(dir)) if (/^v\d+_\d+_\d+-.*\.wasm$/.test(f)) found.push(path.join(dir, f));
    }
  }
  if (!found.length) throw new Error('engine wasm not found: run `cambc mapeditor` once (or any cambc build) so the asset cache exists, or set CAMBC_CACHE');
  found.sort((a, b) => path.basename(a).localeCompare(path.basename(b), undefined, { numeric: true }));
  return found[found.length - 1];
}

export async function loadEngine(wasmPath = findEngineWasm()) {
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst);
  const X = inst.exports;
  const out = X.Engine_Malloc(64);
  const mem = () => new DataView(X.memory.buffer);
  const cstr = (p) => { const u = new Uint8Array(X.memory.buffer); let s = ''; while (u[p]) s += String.fromCharCode(u[p++]); return s; };
  const chk = (r, what) => { if (r !== 0) throw new Error(`${what}: engine code ${r}: ${cstr(X.GetLastErrorMsg())}`); };
  return { X, out, mem, chk };
}

export const SYM = { horizontal: 0, vertical: 1, rot180: 2 };
export const CAMP = { wolf: 0, elk: 1, gem: 2, gold: 3, monolith: 4 };

export class Builder {
  constructor(E, w, h, sym) {
    this.E = E; this.w = w; this.h = h; this.sym = sym;
    E.chk(E.X.MapBuilder_Create(w, h, sym, E.out), 'create');
    this.h_ = E.mem().getBigUint64(E.out, true);
  }
  call(name, ...args) { this.E.chk(this.E.X[name](this.h_, ...args), name); }
  wall(x, y) { this.call('MapBuilder_AddWall', x, y); }
  bush(x, y) { this.call('MapBuilder_AddBush', x, y); }
  hole(x, y) { this.call('MapBuilder_AddHole', x, y); }
  altar(x, y) { this.call('MapBuilder_AddAltar', x, y); }
  camp(type, x, y) { this.E.chk(this.E.X.MapBuilder_AddCamp(this.h_, type, x, y, this.E.out), `camp ${type}@${x},${y}`); }
  champs(n) { this.call('MapBuilder_SetNumChampsPerTeam', n); }
  spawn(minX, minY, maxX, maxY) {
    const m = this.E.mem();
    m.setInt32(this.E.out, minX, true); m.setInt32(this.E.out + 4, minY, true);
    m.setInt32(this.E.out + 8, maxX, true); m.setInt32(this.E.out + 12, maxY, true);
    this.E.chk(this.E.X.MapBuilder_SetTeamASpawnArea(this.h_, this.E.out), 'spawn');
  }
  query(name, x, y) { this.E.chk(this.E.X[name](this.h_, x, y, this.E.out), name); return this.E.mem().getUint8(this.E.out) !== 0; }
  isWall(x, y) { return this.query('MapBuilder_GetWall', x, y); }
  numCamps() { this.E.chk(this.E.X.MapBuilder_GetNumCamps(this.h_, this.E.out), 'ncamps'); return this.E.mem().getUint32(this.E.out, true); }
  encode() {
    this.call('MapBuilder_VerifyIntegrity');
    const { X, out, mem } = this.E;
    this.E.chk(X.MapBuilder_Encode(this.h_, out, out + 4), 'encode');
    const p = mem().getUint32(out, true), n = mem().getUint32(out + 4, true);
    return new Uint8Array(X.memory.buffer, p, n).slice();
  }
  destroy() { this.E.X.MapBuilder_Destroy(this.h_); }
}
