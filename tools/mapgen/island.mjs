// Maps with walled "islands": camp clusters enclosed by a wall ring, reachable only with a teleport crystal
// (range 3, ignores terrain). Usage: node island.mjs <outDir>
import fs from 'node:fs';
import path from 'node:path';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';

const outDir = process.argv[2] || 'maps';
const E = await loadEngine();

function build(name, w, h, sym, champs, spawn, altars, islands, camps) {
  const b = new Builder(E, w, h, sym);
  b.champs(champs);
  b.spawn(...spawn);
  for (const [x, y] of altars) b.altar(x, y);
  for (const { x0, y0, x1, y1, inner } of islands) {
    // wall ring of thickness 1 around [x0..x1]x[y0..y1]
    for (let x = x0 - 1; x <= x1 + 1; x++) { b.wall(x, y0 - 1); b.wall(x, y1 + 1); }
    for (let y = y0; y <= y1; y++) { b.wall(x0 - 1, y); b.wall(x1 + 1, y); }
    for (const [t, x, y] of inner) b.camp(t, x, y);
  }
  for (const [t, x, y] of camps) b.camp(t, x, y);
  fs.writeFileSync(path.join(outDir, name + '.map26a'), b.encode());
  b.destroy();
  console.log('wrote', name);
}

// 40x40 rot180: one island with two gem clusters and a wolf on our half.
build('isl_40x40_R_c3', 40, 40, SYM.rot180, 3, [1, 1, 4, 4], [[8, 3], [16, 10]],
  [{ x0: 4, y0: 12, x1: 9, y1: 16, inner: [[CAMP.gem, 5, 13], [CAMP.gem, 8, 15], [CAMP.wolf, 6, 15]] }],
  [[CAMP.gem, 12, 3], [CAMP.wolf, 14, 7], [CAMP.gold, 3, 9]]);

// 56x56 horizontal: an island with an elk and gems, plus ordinary camps.
build('isl_56x56_H_c4', 56, 56, SYM.horizontal, 4, [2, 25, 5, 29], [[9, 27], [20, 14], [20, 42]],
  [{ x0: 12, y0: 4, x1: 18, y1: 9, inner: [[CAMP.gem, 13, 5], [CAMP.gem, 17, 8], [CAMP.elk, 15, 6]] }],
  [[CAMP.gem, 10, 20], [CAMP.wolf, 14, 30], [CAMP.wolf, 15, 30], [CAMP.gem, 8, 40], [CAMP.wolf, 18, 45]]);

// 64x64 vertical: two small islands.
build('isl_64x64_V_c5', 64, 64, SYM.vertical, 5, [30, 2, 33, 5], [[31, 10], [12, 20], [50, 20]],
  [{ x0: 6, y0: 6, x1: 10, y1: 9, inner: [[CAMP.gem, 7, 7], [CAMP.wolf, 9, 8]] },
   { x0: 52, y0: 6, x1: 56, y1: 9, inner: [[CAMP.gem, 53, 7], [CAMP.gem, 55, 8]] }],
  [[CAMP.gem, 20, 10], [CAMP.wolf, 40, 12], [CAMP.wolf, 41, 12], [CAMP.gem, 30, 22], [CAMP.elk, 15, 25], [CAMP.wolf, 48, 26]]);
