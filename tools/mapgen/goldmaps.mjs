// Gem-scarce ("gold") test maps: gold clusters everywhere, gems only from monoliths and/or a few elks or far
// wolves, so that no team reaches winning_gems by the round limit and the engine's tiebreakers decide
// (banked gems, then gold earned, then kills, then team B). Plus control maps where gems are scarce but
// reachable. Symmetric and connectivity-checked like gen.mjs; every map is encoded by the engine's own
// MapBuilder (VerifyIntegrity).
//
// Usage: node tools/mapgen/goldmaps.mjs [outDir=maps/gold] [seed=7]
import fs from 'node:fs';
import path from 'node:path';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';

const [outDir = 'maps/gold', seedArg = '7'] = process.argv.slice(2);
let seed = Number(seedArg) >>> 0 || 7;
const rnd = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed / 4294967296; };
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];

function mirror(sym, w, h, x, y) {
  if (sym === SYM.horizontal) return [w - 1 - x, y];
  if (sym === SYM.vertical) return [x, h - 1 - y];
  return [w - 1 - x, h - 1 - y];
}
function inHalfA(sym, w, h, x, y, margin = 1) {
  if (sym === SYM.horizontal) return x < Math.floor(w / 2) - margin;
  if (sym === SYM.vertical) return y < Math.floor(h / 2) - margin;
  return (x + y) < (w + h) / 2 - 1 - margin;
}

// recipe: { name, w, h, sym, champs, groups: [{ type, n (camps), count, where }], altars, walls, bushes, holes }
// where: 'home' (within a third of the map from our spawn), 'mid' (between), 'center' (near the mirror line),
//        'far' (our half, but farther from our spawn than most), 'any'.
function makeMap(E, R) {
  const { w, h, sym, champs } = R;
  const area = w * h;
  const g = new Uint8Array(w * h);
  const at = (x, y) => g[y * w + x];
  const inb = (x, y) => x >= 0 && y >= 0 && x < w && y < h;
  const setBoth = (x, y, v) => { const [mx, my] = mirror(sym, w, h, x, y); g[y * w + x] = v; g[my * w + mx] = v; };
  const free = (x, y) => inb(x, y) && at(x, y) === 0;

  const sw = 3, sh = 3;
  let sx, sy;
  const edge = ri(1, 3);
  if (sym === SYM.horizontal) { sx = edge; sy = ri(Math.floor(h / 3), Math.floor(2 * h / 3) - sh); }
  else if (sym === SYM.vertical) { sy = edge; sx = ri(Math.floor(w / 3), Math.floor(2 * w / 3) - sw); }
  else { sx = edge; sy = edge + ri(0, Math.floor(h / 6)); }
  for (let y = sy - 1; y <= sy + sh; y++) for (let x = sx - 1; x <= sx + sw; x++) if (inb(x, y)) setBoth(x, y, 7);
  for (let y = sy; y < sy + sh; y++) for (let x = sx; x < sx + sw; x++) setBoth(x, y, 6);
  const spawnC = [sx + 1, sy + 1];
  const dSpawn = (x, y) => Math.max(Math.abs(x - spawnC[0]), Math.abs(y - spawnC[1]));
  const dMirror = (x, y) => { const [mx, my] = mirror(sym, w, h, x, y); return Math.max(Math.abs(mx - x), Math.abs(my - y)); };
  const span = Math.max(w, h);
  const wherePred = {
    home: (x, y) => dSpawn(x, y) <= span / 3,
    mid: (x, y) => dSpawn(x, y) > span / 5 && dMirror(x, y) > 6,
    center: (x, y) => dMirror(x, y) <= Math.max(8, Math.min(w, h) / 4) && dSpawn(x, y) >= span / 4,
    far: (x, y) => dSpawn(x, y) >= span / 2.5,
    any: () => true,
  };
  const randHalfTile = (tries, pred) => {
    for (let t = 0; t < tries; t++) {
      const x = ri(1, w - 2), y = ri(1, h - 2);
      if (inHalfA(sym, w, h, x, y) && pred(x, y)) return [x, y];
    }
    return null;
  };
  const clearAround = (x, y, r) => { for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (inb(x + dx, y + dy) && at(x + dx, y + dy) !== 0) return false; return true; };

  const camps = [];
  const placeGroup = (type, n, where, extra = []) => {
    n = Math.max(n, 1 + extra.length);
    const pr = wherePred[where] ?? wherePred.any;
    const p = randHalfTile(2000, (x, y) => clearAround(x, y, 2) && pr(x, y));
    if (!p) return false;
    const cells = [p];
    const dirs = [[1, 0], [0, 1], [-1, 0], [0, -1]];
    let guard = 0;
    while (cells.length < n && guard++ < 200) {
      const [cx, cy] = pick(cells), [dx, dy] = pick(dirs);
      const nx = cx + dx, ny = cy + dy;
      if (inb(nx, ny) && at(nx, ny) === 0 && inHalfA(sym, w, h, nx, ny) && !cells.some(([a, b]) => a === nx && b === ny)) cells.push([nx, ny]);
    }
    if (cells.length < n) return false;
    cells.forEach(([x, y], i) => { setBoth(x, y, 5); camps.push([i === 0 ? type : (extra[i - 1] ?? type), x, y]); });
    for (const [x, y] of cells) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (inb(x + dx, y + dy) && at(x + dx, y + dy) === 0) setBoth(x + dx, y + dy, 7);
    return true;
  };
  for (const gr of R.groups)
    for (let i = 0; i < (gr.count ?? 1); i++)
      if (!placeGroup(gr.type, gr.n ?? 1, gr.where ?? 'any', gr.with ?? [])) return null;

  const nAltar = R.altars ?? 2;
  const altars = [];
  for (let i = 0; i < nAltar; i++) {
    const p = randHalfTile(2000, (x, y) => clearAround(x, y, 2) && (i > 0 || dSpawn(x, y) < Math.max(8, Math.min(w, h) / 4)));
    if (!p) continue;
    setBoth(p[0], p[1], 4); altars.push(p);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (free(p[0] + dx, p[1] + dy)) setBoth(p[0] + dx, p[1] + dy, 7);
  }
  if (altars.length === 0) return null;

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
  paint(1, R.walls ?? 0.06, 'line');
  paint(2, R.bushes ?? 0.04, 'blob');
  paint(3, R.holes ?? 0, 'line');

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
  const [ex, ey] = mirror(sym, w, h, sx, sy);
  if (!seen[ey * w + ex]) return null;
  for (const [, x, y] of camps) { if (!touched(x, y)) return null; const [mx, my] = mirror(sym, w, h, x, y); if (!touched(mx, my)) return null; }
  for (const [x, y] of altars) { if (!touched(x, y)) return null; }

  const b = new Builder(E, w, h, sym);
  try {
    b.champs(champs);
    b.spawn(sx, sy, sx + sw, sy + sh);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const v = at(x, y);
      if (v === 1) b.wall(x, y); else if (v === 2) b.bush(x, y); else if (v === 3) b.hole(x, y);
    }
    for (const [x, y] of altars) b.altar(x, y);
    for (const [t, x, y] of camps) b.camp(t, x, y);
    return { bytes: b.encode(), altars: altars.length };
  } catch (e) {
    return null;
  } finally { b.destroy(); }
}

const H = SYM.horizontal, V = SYM.vertical, R = SYM.rot180;
const gold = (count, n, where = 'any') => ({ type: CAMP.gold, n, count, where });
const recipes = [
  // Tiebreak maps: gems only from the monolith (200 gems / 300 gold, 20,000 HP, 200 str, respawn 150), elks or far wolves.
  { name: 'gold_mono_36x36_R_c3', w: 36, h: 36, sym: R, champs: 3,
    groups: [{ type: CAMP.monolith, where: 'center' }, gold(3, 1, 'home'), gold(2, 2, 'mid'), gold(1, 3, 'far')] },
  { name: 'gold_mono_48x48_H_c4', w: 48, h: 48, sym: H, champs: 4,
    groups: [{ type: CAMP.monolith, where: 'center' }, gold(4, 1, 'home'), gold(2, 2, 'mid'), gold(2, 3, 'any')] },
  { name: 'gold_mono_64x64_V_c5', w: 64, h: 64, sym: V, champs: 5, walls: 0.08,
    groups: [{ type: CAMP.monolith, where: 'center' }, gold(4, 1, 'home'), gold(3, 2, 'mid'), gold(3, 3, 'any')] },
  { name: 'gold_monoelk_56x56_R_c5', w: 56, h: 56, sym: R, champs: 5,
    groups: [{ type: CAMP.monolith, where: 'center' }, { type: CAMP.elk, n: 1, where: 'far' }, gold(4, 1, 'home'), gold(3, 2, 'mid'), gold(2, 3, 'any')] },
  { name: 'gold_elk_44x44_R_c4', w: 44, h: 44, sym: R, champs: 4,
    groups: [{ type: CAMP.elk, n: 1, where: 'far' }, gold(4, 1, 'home'), gold(3, 2, 'mid'), gold(1, 3, 'far')] },
  { name: 'gold_elkwolf_60x60_H_c4', w: 60, h: 60, sym: H, champs: 4,
    groups: [{ type: CAMP.elk, n: 1, where: 'center' }, { type: CAMP.wolf, n: 1, where: 'center' }, gold(5, 1, 'any'), gold(3, 2, 'mid')] },
  { name: 'gold_monowolf_72x72_V_c5', w: 72, h: 72, sym: V, champs: 5, walls: 0.07,
    groups: [{ type: CAMP.monolith, where: 'center' }, { type: CAMP.wolf, n: 1, where: 'center' }, gold(5, 1, 'home'), gold(3, 2, 'mid'), gold(3, 3, 'far')] },
  { name: 'gold_mono_30x30_V_c3', w: 30, h: 30, sym: V, champs: 3,
    groups: [{ type: CAMP.monolith, where: 'center' }, gold(2, 1, 'home'), gold(2, 2, 'any')] },
  { name: 'gold_monoelk2_80x80_H_c5', w: 80, h: 80, sym: H, champs: 5, walls: 0.08,
    groups: [{ type: CAMP.monolith, where: 'mid' }, { type: CAMP.elk, n: 2, where: 'center' }, gold(5, 1, 'home'), gold(4, 2, 'mid'), gold(3, 3, 'far')] },
  // Controls: gems scarce but reachable (gem clusters and wolves on our half, gold everywhere).
  { name: 'ctrl_scarce_50x50_R_c4', w: 50, h: 50, sym: R, champs: 4,
    groups: [{ type: CAMP.gem, n: 1, count: 2, where: 'mid' }, { type: CAMP.wolf, n: 2, count: 1, where: 'mid' }, { type: CAMP.elk, n: 1, where: 'far' }, gold(4, 1, 'any'), gold(2, 2, 'any')] },
  { name: 'ctrl_scarce_58x58_V_c5', w: 58, h: 58, sym: V, champs: 5,
    groups: [{ type: CAMP.gem, n: 1, count: 2, where: 'home' }, { type: CAMP.wolf, n: 1, count: 2, where: 'mid' }, { type: CAMP.monolith, where: 'center' }, gold(5, 1, 'any'), gold(2, 2, 'any')] },
  // Harder: the only gem source is a monolith fused with elks (one group: every camp must die before the capture).
  { name: 'gold_monoEE_40x40_R_c3', w: 40, h: 40, sym: R, champs: 3,
    groups: [{ type: CAMP.monolith, where: 'center', with: [CAMP.elk, CAMP.elk] }, gold(3, 1, 'home'), gold(2, 2, 'mid'), gold(1, 3, 'any')] },
  { name: 'gold_monoE_52x52_H_c4', w: 52, h: 52, sym: H, champs: 4,
    groups: [{ type: CAMP.monolith, where: 'center', with: [CAMP.elk] }, gold(4, 1, 'home'), gold(2, 2, 'mid'), gold(2, 3, 'any')] },
  { name: 'gold_monoEE_68x68_V_c5', w: 68, h: 68, sym: V, champs: 5, walls: 0.07,
    groups: [{ type: CAMP.monolith, where: 'center', with: [CAMP.elk, CAMP.elk] }, gold(5, 1, 'home'), gold(3, 2, 'mid'), gold(3, 3, 'any')] },
];

const E = await loadEngine();
fs.mkdirSync(outDir, { recursive: true });
const index = [];
for (const r of recipes) {
  let m = null, tries = 0;
  while (!m && tries++ < 400) m = makeMap(E, r);
  if (!m) { console.log('FAILED', r.name); continue; }
  fs.writeFileSync(path.join(outDir, r.name + '.map26a'), m.bytes);
  index.push({ name: r.name, w: r.w, h: r.h, sym: r.sym, champs: r.champs, altars: m.altars, tries });
  console.log('wrote', r.name, 'after', tries, 'tries');
}
fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify(index, null, 1));
