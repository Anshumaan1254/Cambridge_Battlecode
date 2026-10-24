#!/usr/bin/env node
// Decode a replay once (cache as gz JSON with terrain) and report hole-pocket occupancy per team:
// a tile is a "pocket" tile for team t when no 8-connected walk over non-wall, non-hole, non-altar, non-enemy-spawn tiles reaches t's spawn
// (the bot's W.dist_home(p) >= BIG). One JSON line per replay.
//   node pk.mjs CACHE_DIR replay...
import fs from 'node:fs';
import zlib from 'node:zlib';
import { WASI } from 'node:wasi';
import { decode, findEngineWasms, unwrapReplay } from 'file:///C:/battlecode/Cambridge_Battlecode/tools/replay/decode.mjs';
process.removeAllListeners('warning');
const CACHE = process.argv[2];

async function terrainOf(buf) {
  buf = unwrapReplay(buf);
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst);
  const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
  const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load');
  const g = dv().getBigUint64(out, true);
  chk(X.Game_GetBitboardMetadata(g, out), 'meta');
  const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
  chk(X.Game_GetSymmetry(g, out), 'sym'); const sym = dv().getInt32(out, true);
  chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
  const sp = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
  const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return dv().getUint8(out) !== 0; };
  const grid = [];
  for (let y = 0; y < h; y++) {
    let row = '';
    for (let x = 0; x < w; x++) row += tile('Game_GetWall', x, y) ? '#' : tile('Game_GetHole', x, y) ? 'o' : tile('Game_GetAltar', x, y) ? 'A' : '.';
    grid.push(row);
  }
  return { w, h, sym, sp, grid };
}

for (const file of process.argv.slice(3)) {
  const base = file.split(/[\\/]/).pop().replace(/\.repl26a$/, '');
  let d, T;
  const cf = `${CACHE}/${base}.json.gz`;
  try {
    if (fs.existsSync(cf)) ({ d, T } = JSON.parse(zlib.gunzipSync(fs.readFileSync(cf))));
    else {
      const buf = fs.readFileSync(file);
      d = await decode(buf);
      T = await terrainOf(buf);
      fs.writeFileSync(cf, zlib.gzipSync(JSON.stringify({ d, T })));
    }
  } catch (e) { console.error(file, e.message); continue; }
  const { w, h, sym, sp, grid } = T;
  // spawn tiles: engine area for team A (x0,y0,x1,y1 exclusive end as mapinfo.mjs reads it, widened by the round-1 positions), mirrored for B
  const mirror = (x, y) => sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y];
  const spawn = [new Set(), new Set()];
  for (let y = sp[1]; y <= sp[3]; y++) for (let x = sp[0]; x <= sp[2]; x++) {
    if (x < 0 || y < 0 || x >= w || y >= h) continue;
    if (y < sp[3] && x < sp[2]) { spawn[0].add(y * w + x); const [mx, my] = mirror(x, y); spawn[1].add(my * w + mx); }
  }
  const r1 = d.rounds.find((s) => s && s.r >= 1);
  for (const c of r1.ch) spawn[c[1]].add(c[4] * w + c[3]);
  const reach = [0, 1].map((t) => {
    const blocked = (i) => grid[Math.floor(i / w)][i % w] !== '.' || spawn[1 - t].has(i);
    const seen = new Uint8Array(w * h);
    const q = [];
    for (const i of spawn[t]) { seen[i] = 1; q.push(i); }
    while (q.length) {
      const i = q.pop(); const x = i % w, y = Math.floor(i / w);
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const j = ny * w + nx; if (seen[j] || blocked(j)) continue; seen[j] = 1; q.push(j);
      }
    }
    return seen;
  });
  // active events per body per round (attack / cast / capture gems / bank)
  const act = new Map();
  for (const e of d.events) if (e.who !== undefined && ['Attack', 'Cast ability', 'CaptureGems', 'Gems submitted', 'Banked'].includes(e.k)) act.set(`${e.who}:${e.r}`, 1);
  const out = { file: base, w, h, teams: {} };
  for (const t of [0, 1]) {
    let pr = 0; const runs = [];
    for (const b of d.meta.bodies.filter((b) => b.team === t)) {
      let cur = null;
      const close = () => { if (cur && cur.rounds >= 5) runs.push(cur); cur = null; };
      for (const s of d.rounds) {
        if (!s) continue;
        const c = s.ch.find((q) => q[0] === b.index);
        if (!c || !c[7]) { if (cur) cur.endHow = 'death/absent'; close(); continue; }
        const i = c[4] * w + c[3];
        if (!reach[t][i]) {
          pr++;
          if (!cur) cur = { type: b.type, body: b.index, from: s.r, rounds: 0, tiles: new Set(), acts: 0, idle: 0, maxIdle: 0, at: [c[3], c[4]], gems0: c[8], hp0: c[5] };
          cur.rounds++; cur.tiles.add(i); cur.last = [c[3], c[4]]; cur.gems1 = c[8]; cur.hp1 = c[5];
          if (act.has(`${b.index}:${s.r}`)) { cur.acts++; cur.idle = 0; } else { cur.idle++; cur.maxIdle = Math.max(cur.maxIdle, cur.idle); }
        } else { if (cur) cur.endHow = 'walked/dashed out'; close(); }
      }
      if (cur) cur.endHow = 'game end'; close();
    }
    out.teams[t] = { pocketRounds: pr, runs: runs.sort((a, b) => b.rounds - a.rounds).map((r) => ({ ...r, tiles: r.tiles.size })) };
  }
  console.log(JSON.stringify(out));
}
