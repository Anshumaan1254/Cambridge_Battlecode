// Rules-probe map for tools/mapintel/probe_rules (40x40, rot180; everything is placed in the bottom-left quadrant, the engine mirrors it).
// Layout (team A spawn tiles 1..3 x 1..3); the probe bot rules_main.cpp walks its three bodies to these tiles:
//   Stellar: LOS test S3 (2,16) with walls (3,15..17) and gem L (5,16); S0 (6,9): gems C2 (10,9) d(4,0), C1 (9,12) d(3,3), C3 (10,13) d(4,4),
//            AoE centre Q (6,13) with gems (7,14) Q+(1,1), (8,13) Q+(2,0), (5,12) Q+(-1,-1); S1 (13,12): wolf W (16,9) d(3,-3);
//            S2 (10,14): elk E (6,18) d(-4,4).
//   Ryth: gem M1 (2,7) (melee diagonal attack from (1,6), capture, stand on the dead tile 70 rounds), altar AL (5,5) (tribute from (7,7)
//         = distance 2, then from (6,6) = diagonal 1).
//   Vendetta: dash tests (a) holes (9,1..3) from (8,2) to (10,2); (e) from (10,2) onto the hole (9,3); (b) walls (13,1..3) from (12,2) to
//         (14,2); (c) hole (17,2) from (16,1) to (18,3); (d) wall (17,5) + hole (17,6) from (16,5) to (18,6); (f) gem G6 (15,7) with walls
//         (15,6), (15,8) from (14,7) to (16,7); crystal tests after a gold cluster GC (1,9): walls (2,11..13), hole (1,15); from (1,12):
//         (k) to (5,12) distance 4, (j) to the hole (1,15), (h) over the walls to (4,12); then (i) from (4,12) to (7,15) diagonal 3.
import fs from 'node:fs';
import { loadEngine, Builder, SYM, CAMP } from '../../mapgen/engine.mjs';
const E = await loadEngine();
const b = new Builder(E, 40, 40, SYM.rot180);
b.champs(3);
b.spawn(1, 1, 4, 4);
const gem = (x, y) => b.camp(CAMP.gem, x, y);
// Stellar
for (const y of [15, 16, 17]) b.wall(3, y);
gem(5, 16); gem(10, 9); gem(9, 12); gem(10, 13); gem(7, 14); gem(8, 13); gem(5, 12);
b.camp(CAMP.wolf, 16, 9); b.camp(CAMP.elk, 6, 18);
// Ryth
gem(2, 7); b.altar(5, 5);
// Vendetta: dash
for (const y of [1, 2, 3]) { b.hole(9, y); b.wall(13, y); }
b.hole(17, 2); b.wall(17, 5); b.hole(17, 6);
gem(15, 7); b.wall(15, 6); b.wall(15, 8);
// Vendetta: crystal
b.camp(CAMP.gold, 1, 9);
for (const y of [11, 12, 13]) b.wall(2, y);
b.hole(1, 15);
const out = process.argv[2] || new URL('../../../maps/probe_mi/mi_rules.map26a', import.meta.url);
fs.writeFileSync(out, b.encode());
console.log('ok', b.numCamps());
