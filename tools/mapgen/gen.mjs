// Generate a diverse, symmetric, connectivity-checked map pool for local testing.
// Usage: node gen.mjs <outDir> <count> [seed]
import fs from 'node:fs';
import path from 'node:path';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';

const [outDir = 'maps', countArg = '24', seedArg = '1'] = process.argv.slice(2);
let seed = Number(seedArg) >>> 0 || 1;
const rnd = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed / 4294967296; };
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];

function mirror(sym, w, h, x, y) {
  if (sym === SYM.horizontal) return [w - 1 - x, y];
  if (sym === SYM.vertical) return [x, h - 1 - y];
  return [w - 1 - x, h - 1 - y];
}

// Team A's half: tiles strictly closer to A's side than their mirror is.
function inHalfA(sym, w, h, x, y, margin = 1) {
  if (sym === SYM.horizontal) return x < Math.floor(w / 2) - margin;
  if (sym === SYM.vertical) return y < Math.floor(h / 2) - margin;
  return (x + y) < (w + h) / 2 - 1 - margin;
}

function makeMap(E, idx, opts = {}) {
  const sizeBucket = opts.size ?? pick([30, 36, 40, 44, 50, 56, 64, 72, 80, 100]);
  const w = opts.w ?? Math.max(30, Math.min(100, sizeBucket + ri(-4, 4)));
  const h = opts.h ?? Math.max(30, Math.min(100, sizeBucket + ri(-4, 4)));
  const sym = opts.sym ?? pick([SYM.horizontal, SYM.vertical, SYM.rot180, SYM.rot180]);
  const champs = opts.champs ?? pick([3, 4, 4, 5, 5]);
  const area = w * h;

  // tile grid: 0 ground, 1 wall, 2 bush, 3 hole, 4 altar, 5 camp, 6 spawn, 7 reserved(no terrain)
  const g = new Uint8Array(w * h);
  const at = (x, y) => g[y * w + x];
  const inb = (x, y) => x >= 0 && y >= 0 && x < w && y < h;
  const setBoth = (x, y, v) => { const [mx, my] = mirror(sym, w, h, x, y); g[y * w + x] = v; g[my * w + mx] = v; };
  const free = (x, y) => inb(x, y) && at(x, y) === 0;

  // Spawn: corner for rot180, side for reflections.
  const sw = ri(3, 4), sh = (sw === 4 ? ri(3, 4) : 3) ;
  let sx, sy;
  const edge = ri(1, Math.max(2, Math.floor(Math.min(w, h) / 12)));
  if (sym === SYM.horizontal) { sx = edge; sy = ri(2, h - sh - 2); }
  else if (sym === SYM.vertical) { sy = edge; sx = ri(2, w - sw - 2); }
  else { sx = edge; sy = edge + ri(0, Math.floor(h / 5)); }
  for (let y = sy - 1; y <= sy + sh; y++) for (let x = sx - 1; x <= sx + sw; x++) if (inb(x, y)) setBoth(x, y, 7);
  for (let y = sy; y < sy + sh; y++) for (let x = sx; x < sx + sw; x++) setBoth(x, y, 6);
  const spawnC = [sx + (sw >> 1), sy + (sh >> 1)];

  const randHalfTile = (tries = 400, pred = () => true) => {
    for (let t = 0; t < tries; t++) {
      const x = ri(1, w - 2), y = ri(1, h - 2);
      if (inHalfA(sym, w, h, x, y) && pred(x, y)) return [x, y];
    }
    return null;
  };
  const clearAround = (x, y, r) => { for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (inb(x + dx, y + dy) && at(x + dx, y + dy) !== 0) return false; return true; };

  // Camps (placed before terrain so terrain avoids them).
  const camps = [];
  const placeGroup = (type, n, minR = 2, pred = () => true) => {
    const p = randHalfTile(600, (x, y) => clearAround(x, y, minR) && pred(x, y));
    if (!p) return false;
    const cells = [p];
    const dirs = [[1, 0], [0, 1], [-1, 0], [0, -1]];
    while (cells.length < n) {
      const [cx, cy] = pick(cells), [dx, dy] = pick(dirs);
      const nx = cx + dx, ny = cy + dy;
      if (inb(nx, ny) && at(nx, ny) === 0 && inHalfA(sym, w, h, nx, ny) && !cells.some(([a, b]) => a === nx && b === ny)) cells.push([nx, ny]);
      else if (rnd() < 0.05) break;
    }
    for (const [x, y] of cells) { setBoth(x, y, 5); camps.push([type, x, y]); }
    // keep a ring of ground around the group so it is reachable
    for (const [x, y] of cells) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (inb(x + dx, y + dy) && at(x + dx, y + dy) === 0) setBoth(x + dx, y + dy, 7);
    return true;
  };
  const scale = Math.sqrt(area / 2500);
  const nGem = Math.max(1, Math.round(ri(2, 4) * scale));
  const nGold = Math.round(ri(0, 2) * scale);
  const nWolf = Math.max(1, Math.round(ri(2, 5) * scale));
  const nElk = Math.round(ri(0, 3) * scale);
  for (let i = 0; i < nGem; i++) placeGroup(CAMP.gem, rnd() < 0.3 ? 2 : 1);
  for (let i = 0; i < nGold; i++) placeGroup(CAMP.gold, 1);
  for (let i = 0; i < nWolf; i++) placeGroup(CAMP.wolf, pick([1, 1, 2, 2, 3]));
  for (let i = 0; i < nElk; i++) placeGroup(CAMP.elk, pick([1, 1, 2]));
  if (opts.monolith ?? rnd() < 0.6) {
    // near the centre, on our half
    placeGroup(CAMP.monolith, 1, 2, (x, y) => {
      const [mx, my] = mirror(sym, w, h, x, y); return Math.max(Math.abs(mx - x), Math.abs(my - y)) <= Math.max(8, Math.min(w, h) / 4);
    });
  }

  // Altars: one near our spawn-ish area, one mid-way, sometimes a third.
  const nAltar = opts.altars ?? pick([1, 2, 2, 3]);
  const altars = [];
  for (let i = 0; i < nAltar; i++) {
    const p = randHalfTile(800, (x, y) => clearAround(x, y, 2) && (i > 0 || Math.max(Math.abs(x - spawnC[0]), Math.abs(y - spawnC[1])) < Math.max(10, Math.min(w, h) / 3)));
    if (!p) continue;
    setBoth(p[0], p[1], 4); altars.push(p);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (free(p[0] + dx, p[1] + dy)) setBoth(p[0] + dx, p[1] + dy, 7);
  }
  if (altars.length === 0) return null;

  // Terrain: wall segments, bush patches, hole lines.
  const wallFrac = opts.walls ?? (0.04 + rnd() * 0.10);
  const bushFrac = opts.bushes ?? (0.02 + rnd() * 0.06);
  const holeFrac = opts.holes ?? (rnd() < 0.5 ? 0 : 0.01 + rnd() * 0.04);
  const paint = (v, frac, mode) => {
    let budget = Math.floor(area * frac / 2);
    let guard = 0;
    while (budget > 0 && guard++ < 5000) {
      let [x, y] = [ri(1, w - 2), ri(1, h - 2)];
      if (!inHalfA(sym, w, h, x, y, 0)) continue;
      const len = mode === 'line' ? ri(3, 10) : ri(3, 12);
      let [dx, dy] = pick([[1, 0], [0, 1], [1, 1], [1, -1]]);
      for (let k = 0; k < len && budget > 0; k++) {
        if (free(x, y)) { setBoth(x, y, v); budget--; }
        if (mode === 'blob') { [dx, dy] = pick([[1, 0], [0, 1], [-1, 0], [0, -1]]); }
        x += dx; y += dy;
        if (!inb(x, y)) break;
      }
    }
  };
  paint(1, wallFrac, 'line');
  paint(2, bushFrac, 'blob');
  paint(3, holeFrac, 'line');

  // Connectivity: every camp neighbourhood and altar must be reachable from spawn by walking.
  const passable = (x, y) => inb(x, y) && at(x, y) !== 1 && at(x, y) !== 3 && at(x, y) !== 4 && at(x, y) !== 5;
  const seen = new Uint8Array(w * h);
  const q = [[sx, sy]]; seen[sy * w + sx] = 1;
  while (q.length) {
    const [x, y] = q.pop();
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const nx = x + dx, ny = y + dy;
      if (passable(nx, ny) && !seen[ny * w + nx]) { seen[ny * w + nx] = 1; q.push([nx, ny]); }
    }
  }
  const touched = (x, y) => { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (inb(x + dx, y + dy) && seen[(y + dy) * w + x + dx]) return true; return false; };
  // Enemy spawn reachability (mirror) too.
  const [ex, ey] = mirror(sym, w, h, sx, sy);
  if (!seen[ey * w + ex]) return null;
  for (const [, x, y] of camps) { if (!touched(x, y)) return null; const [mx, my] = mirror(sym, w, h, x, y); if (!touched(mx, my)) return null; }
  for (const [x, y] of altars) { if (!touched(x, y)) return null; }

  // Emit through the engine's MapBuilder (it mirrors terrain, camps and spawn itself).
  const b = new Builder(E, w, h, sym);
  try {
    b.champs(champs);
    b.spawn(sx, sy, sx + sw, sy + sh);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (!inHalfA(sym, w, h, x, y, -1) && !(sym === SYM.rot180 && (x + y) === Math.floor((w + h) / 2) - 1)) {
        // engine mirrors; still emit all tiles idempotently
      }
      const v = at(x, y);
      if (v === 1) b.wall(x, y); else if (v === 2) b.bush(x, y); else if (v === 3) b.hole(x, y);
    }
    for (const [x, y] of altars) b.altar(x, y);
    for (const [t, x, y] of camps) b.camp(t, x, y);
    const bytes = b.encode();
    const counts = camps.reduce((m, [t]) => (m[t] = (m[t] || 0) + 1, m), {});
    const name = `gen${String(idx).padStart(2, '0')}_${w}x${h}_${['H', 'V', 'R'][sym]}_c${champs}`;
    return { name, bytes, info: { w, h, sym, champs, altars: altars.length, camps: counts, walls: wallFrac.toFixed(3), holes: holeFrac.toFixed(3) } };
  } catch (e) {
    return null;
  } finally { b.destroy(); }
}

const E = await loadEngine();
fs.mkdirSync(outDir, { recursive: true });
const want = Number(countArg);
const presets = [
  { size: 30, champs: 3 }, { size: 100, champs: 5 }, { size: 50, holes: 0.06 }, { size: 64, walls: 0.16 },
  { size: 40, monolith: true, champs: 5 }, { size: 72, altars: 1 }, { size: 44, sym: SYM.horizontal }, { size: 56, sym: SYM.vertical },
];
let made = 0, attempts = 0;
const index = [];
while (made < want && attempts < want * 200) {
  attempts++;
  const m = makeMap(E, made, presets[made] ?? {});
  if (!m) continue;
  fs.writeFileSync(path.join(outDir, m.name + '.map26a'), m.bytes);
  index.push({ name: m.name, ...m.info });
  made++;
}
fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify(index, null, 1));
console.log(`made ${made} maps in ${attempts} attempts`);
for (const m of index) console.log(m.name, JSON.stringify(m.camps), 'altars', m.altars);
