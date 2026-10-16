// Approximate replicas of ladder maps, reconstructed from match-summary event coordinates
// (captures, tributes, deaths). Walls and bushes are unknown and omitted.
// Usage: node replica.mjs <outDir>
import fs from 'node:fs';
import path from 'node:path';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';

const outDir = process.argv[2] || 'maps';
const E = await loadEngine();
function build(name, w, h, sym, champs, spawn, altars, lines) {
  const b = new Builder(E, w, h, sym);
  b.champs(champs);
  b.spawn(...spawn);
  for (const [x, y] of altars) b.altar(x, y);
  for (const [t, cells] of lines) for (const [x, y] of cells) b.camp(t, x, y);
  fs.writeFileSync(path.join(outDir, name + '.map26a'), b.encode());
  b.destroy();
  console.log('wrote', name);
}
const vline = (x, y0, n) => Array.from({ length: n }, (_, k) => [x, y0 + k]);
const hline = (x0, y, n) => Array.from({ length: n }, (_, k) => [x0 + k, y]);

// Ladder match 727cae82 (we scored 0): 50x50, 4 champions, rotational symmetry. Per side: three vertical 3-wolf lines
// (66 gems, 4050 HP each) at x=18/31/42, a 0-gem gold column at (1,31-33), altar near (16,17). The centre group is
// unknown (it killed champions); two elks stand in for it. Reconstructed from capture/tribute/death coordinates.
build('rep_727cae82_50x50_R_c4', 50, 50, SYM.rot180, 4, [1, 1, 5, 4], [[16, 17]],
  [[CAMP.wolf, vline(18, 3, 3)], [CAMP.wolf, vline(31, 3, 3)], [CAMP.wolf, vline(42, 3, 3)],
   [CAMP.gold, vline(1, 31, 3)], [CAMP.elk, [[24, 24], [25, 24]]]]);

// Ladder match e7ce6da9 (176-1084): 41x30, 5 champions, left-right mirror, one centre altar at (20,15). Per side:
// single wolf (9,15), 2 wolves (18,10-11), 2 elks (13,3-4) = 72 gems, and 3 elks + gem + gold around (13-15,25-27)
// = 132 gems / 8200 HP.
build('rep_e7ce6da9_41x30_H_c5', 41, 30, SYM.horizontal, 5, [0, 13, 3, 16], [[20, 15]],
  [[CAMP.wolf, [[9, 15]]], [CAMP.wolf, vline(18, 10, 2)], [CAMP.elk, vline(13, 3, 2)],
   [CAMP.elk, vline(13, 25, 3)], [CAMP.gem, [[15, 26]]], [CAMP.gold, [[14, 27]]]]);
