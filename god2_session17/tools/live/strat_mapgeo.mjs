#!/usr/bin/env node
// Map geometry for the strategy analysis (an_strategy): terrain grid, spawns, altars, engine camp groups and walking (BFS)
// distances from both spawns, read from a replay through the engine. One JSON line per replay (pass one replay per map).
// NOTE: a replay-loaded game lists one copy of each mirrored camp group; run tools/live/strat_mapgroups.mjs on the output.
//   CAMBC_CACHE=... node tools/live/strat_mapgeo.mjs replay...
// Output: { file, map, W, H, sym, grid[rows: # wall, o hole, " bush, A altar, . floor], spawnA[[x,y]], spawnB[[x,y]],
//   dA[], dB[] (flat y*W+x walking distance, 8-connected, walls/holes/altars blocked, -1 unreachable),
//   groups[{ i, camps[[x,y,type]], cx, cy, dA, dB, f (dA/(dA+dB)), gems, gold, resp, hp }], altars[[x,y,dA,dB]],
//   feat{ s2s (spawn-to-spawn walk), frontier (walkable tiles with |dA-dB|<=1), frontierRel (/ s2s), midShare (gem rate in
//   0.4<f<0.6 groups), monoMid, golem, elk..., bushMid, holeShare } }
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { findEngineWasms, unwrapReplay } from '../replay/decode.mjs';
process.removeAllListeners('warning');
const TYPES = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem'];
const GEMS = { wolf: 4, elk: 15, gem: 7, gold: 0, monolith: 200, golem: 36 };
const GOLD = { wolf: 40, elk: 90, gem: 0, gold: 20, monolith: 300, golem: 160 };
const RESP = { wolf: 40, elk: 60, gem: 50, gold: 50, monolith: 150, golem: 80 };
const HP = { wolf: 1350, elk: 2400, gem: 120, gold: 120, monolith: 20000, golem: 5000 };
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
  chk(X.Game_GetBitboardMetadata(g, out), 'meta');
  const W = dv().getInt32(out, true), H = dv().getInt32(out + 4, true);
  chk(X.Game_GetSymmetry(g, out), 'sym'); const sym = dv().getInt32(out, true);
  chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
  const sp = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
  const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return dv().getUint8(out) !== 0; };
  const grid = Array.from({ length: H }, () => Array(W).fill('.'));
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (tile('Game_GetWall', x, y)) grid[y][x] = '#';
    else if (tile('Game_GetHole', x, y)) grid[y][x] = 'o';
    else if (tile('Game_GetAltar', x, y)) grid[y][x] = 'A';
    else if (tile('Game_GetBush', x, y)) grid[y][x] = '"';
  }
  const mirror = (x, y) => sym === 0 ? [W - 1 - x, y] : sym === 1 ? [x, H - 1 - y] : [W - 1 - x, H - 1 - y];
  const spawnA = [], spawnB = [];
  for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) if (x < W && y < H) { spawnA.push([x, y]); spawnB.push(mirror(x, y)); }
  const pass0 = (x, y) => x >= 0 && y >= 0 && x < W && y < H && grid[y][x] !== '#' && grid[y][x] !== 'o' && grid[y][x] !== 'A';
  const setA = new Set(spawnA.map(([x, y]) => y * W + x)), setB = new Set(spawnB.map(([x, y]) => y * W + x));
  let block = null; // the enemy spawn cannot be entered
  const pass = (x, y) => pass0(x, y) && !(block && block.has(y * W + x));
  const bfs = (src) => {
    const d = new Int32Array(W * H).fill(-1); const q = [];
    for (const [x, y] of src) { d[y * W + x] = 0; q.push(y * W + x); }
    for (let h = 0; h < q.length; h++) {
      const k = q[h], x = k % W, y = (k - x) / W;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue; const nx = x + dx, ny = y + dy;
        if (!pass(nx, ny) || d[ny * W + nx] >= 0) continue;
        d[ny * W + nx] = d[k] + 1; q.push(ny * W + nx);
      }
    }
    return d;
  };
  block = setB; const dA = bfs(spawnA);
  block = setA; const dB = bfs(spawnB);
  block = null;
  // lane width: vertex-disjoint 8-connected paths from A's spawn to B's spawn (unit vertex capacities, capped at 40)
  const mincut = (() => {
    const N = W * H, cap = new Map(); // edge key -> residual
    const inN = (k) => 2 * k, outN = (k) => 2 * k + 1;
    const adj = Array.from({ length: 2 * N + 2 }, () => []);
    const S = 2 * N, T = 2 * N + 1;
    const add = (u, v, c) => { adj[u].push(v); adj[v].push(u); cap.set(u * 1e6 + v, (cap.get(u * 1e6 + v) || 0) + c); if (!cap.has(v * 1e6 + u)) cap.set(v * 1e6 + u, 0); };
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (!pass0(x, y)) continue; const k = y * W + x;
      const sa = setA.has(k), sb = setB.has(k);
      add(inN(k), outN(k), sa || sb ? 1000 : 1);
      if (sa) add(S, inN(k), 1000); if (sb) add(outN(k), T, 1000);
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { if (!dx && !dy) continue; const nx = x + dx, ny = y + dy; if (pass0(nx, ny)) add(outN(k), inN(ny * W + nx), 1000); }
    }
    let flow = 0;
    while (flow < 40) {
      const prev = new Int32Array(2 * N + 2).fill(-1); prev[S] = S; const q = [S];
      for (let h = 0; h < q.length && prev[T] < 0; h++) { const u = q[h]; for (const v of adj[u]) if (prev[v] < 0 && cap.get(u * 1e6 + v) > 0) { prev[v] = u; q.push(v); } }
      if (prev[T] < 0) break;
      let v = T; while (v !== S) { const u = prev[v]; cap.set(u * 1e6 + v, cap.get(u * 1e6 + v) - 1); cap.set(v * 1e6 + u, cap.get(v * 1e6 + u) + 1); v = u; }
      flow++;
    }
    return flow;
  })();
  // distance to a tile; if blocked, the best walkable neighbour + 1
  const dist = (d, x, y) => {
    if (pass(x, y) && d[y * W + x] >= 0) return d[y * W + x];
    let best = 1e9; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const nx = x + dx, ny = y + dy; if (pass(nx, ny) && d[ny * W + nx] >= 0) best = Math.min(best, d[ny * W + nx] + 1); }
    return best >= 1e9 ? -1 : best;
  };
  chk(X.Game_GetNumCampGroups(g, out), 'ng'); const ng = dv().getUint32(out, true);
  const groups = [];
  for (let i = 0; i < ng; i++) {
    chk(X.Game_GetCampGroupHandle(g, i, out), 'gh'); const gh = dv().getBigUint64(out, true);
    chk(X.Game_GetCampGroup(g, gh, out), 'grp'); const n = dv().getUint32(out + 12, true);
    const camps = [];
    for (let k = 0; k < n; k++) {
      chk(X.Game_GetCampGroupCamp(g, gh, k, out), 'gc'); const ch = dv().getBigUint64(out, true);
      chk(X.Game_GetCamp(g, ch, out), 'c');
      camps.push([dv().getInt32(out + 4, true), dv().getInt32(out + 8, true), TYPES[dv().getInt32(out, true)] ?? dv().getInt32(out, true)]);
    }
    const cx = camps.reduce((a, c) => a + c[0], 0) / n, cy = camps.reduce((a, c) => a + c[1], 0) / n;
    const ga = Math.min(...camps.map((c) => { const v = dist(dA, c[0], c[1]); return v < 0 ? 1e9 : v; }));
    const gb = Math.min(...camps.map((c) => { const v = dist(dB, c[0], c[1]); return v < 0 ? 1e9 : v; }));
    groups.push({ i, camps, cx: +cx.toFixed(1), cy: +cy.toFixed(1), dA: ga, dB: gb, f: +(ga / (ga + gb)).toFixed(3),
      gems: camps.reduce((a, c) => a + (GEMS[c[2]] || 0), 0), gold: camps.reduce((a, c) => a + (GOLD[c[2]] || 0), 0),
      resp: Math.max(...camps.map((c) => RESP[c[2]] || 50)), hp: camps.reduce((a, c) => a + (HP[c[2]] || 0), 0) });
  }
  const altars = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (grid[y][x] === 'A') altars.push([x, y, dist(dA, x, y), dist(dB, x, y)]);
  // features
  const s2s = Math.min(...spawnB.map(([x, y]) => dist(dA, x, y)).filter((v) => v >= 0));
  let frontier = 0, bushMid = 0, midTiles = 0, walk = 0, holes = 0, walls = 0, bushes = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const k = y * W + x, c = grid[y][x];
    if (c === 'o') holes++; if (c === '#') walls++; if (c === '"') bushes++;
    if (dA[k] < 0 || dB[k] < 0) continue;
    walk++;
    if (Math.abs(dA[k] - dB[k]) <= 1) frontier++;
    const f = dA[k] / (dA[k] + dB[k] || 1);
    if (f > 0.4 && f < 0.6) { midTiles++; if (c === '"') bushMid++; }
  }
  const rate = (gs) => gs.reduce((a, g) => a + g.gems / g.resp, 0);
  const mids = groups.filter((g) => g.f > 0.4 && g.f < 0.6);
  const feat = {
    s2s, mincut, frontier, frontierRel: +(frontier / Math.max(1, (W + H) / 2)).toFixed(2), walkShare: +(walk / (W * H)).toFixed(2),
    wall: +(walls / (W * H)).toFixed(3), hole: +(holes / (W * H)).toFixed(3), bush: +(bushes / (W * H)).toFixed(3),
    bushMid: +(bushMid / Math.max(1, midTiles)).toFixed(3),
    groups: groups.length, midGroups: mids.length, midShare: +(rate(mids) / Math.max(1e-9, rate(groups))).toFixed(2),
    gemRate: +rate(groups).toFixed(2), mono: groups.filter((g) => g.camps.some((c) => c[2] === 'monolith')).length,
    monoMid: mids.filter((g) => g.camps.some((c) => c[2] === 'monolith')).length,
    golem: groups.filter((g) => g.camps.some((c) => c[2] === 'golem')).length,
    elk: groups.filter((g) => g.camps.some((c) => c[2] === 'elk')).length,
    heavyMid: mids.filter((g) => g.hp >= 2400).length,
    altars: altars.length, altarMid: altars.filter((a) => { const f = a[2] / (a[2] + a[3]); return f > 0.4 && f < 0.6; }).length,
  };
  const map = path.basename(file).replace(/_[0-9a-f]{8}\.repl26a$/, '');
  console.log(JSON.stringify({ file: path.basename(file), map, W, H, sym, feat, grid: grid.map((r) => r.join('')), spawnA, spawnB,
    dA: Array.from(dA), dB: Array.from(dB), groups, altars }));
}
