// Second rules-probe map (40x40, rot180; bottom-left quadrant only): the rules the first probe left open.
//   Stellar at (6,6): wall column (7,4..8); gem X1 (10,6) behind it; area spell at the ground tile (10,5) (distance 4, not visible).
//   Vendetta: dash through an altar (altar (14,2), walls (14,1), (14,3)) from (13,2) to (15,2); through a bush (bush (14,6), walls (14,5),
//     (14,7)) from (13,6) to (15,6); kill gem G7 (17,10), then dash from (15,10) onto its dead tile; kill gold cluster GC (1,9), buy a
//     crystal, crystal from (15,12) onto G7's dead tile (17,12)? no: onto the altar (14,2) from (13,4)... see rules2_main.cpp.
import fs from 'node:fs';
import { loadEngine, Builder, SYM, CAMP } from '../../mapgen/engine.mjs';
const E = await loadEngine();
const b = new Builder(E, 40, 40, SYM.rot180);
b.champs(3);
b.spawn(1, 1, 4, 4);
for (const y of [4, 5, 6, 7, 8]) b.wall(7, y);
b.camp(CAMP.gem, 10, 6);
b.altar(14, 2); b.wall(14, 1); b.wall(14, 3);
b.bush(14, 6); b.wall(14, 5); b.wall(14, 7);
b.camp(CAMP.gem, 17, 10);
b.camp(CAMP.gold, 1, 9);
b.camp(CAMP.gold, 3, 9);
for (const x of [9, 10]) b.hole(x, 13);
const out = process.argv[2] || new URL('../../../maps/probe_mi/mi_rules2.map26a', import.meta.url);
fs.writeFileSync(out, b.encode());
console.log('ok', b.numCamps());
