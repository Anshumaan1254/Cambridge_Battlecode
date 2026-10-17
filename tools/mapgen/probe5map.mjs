// Session 5 probe map (25x25, rot180): own half has gem clusters near the spawn, centre altar (12,12) is its own mirror.
import fs from 'node:fs';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';
const E = await loadEngine();
const b = new Builder(E, 25, 25, SYM.rot180);
b.champs(5);
b.spawn(1, 1, 5, 5);        // tiles 1..4
b.camp(CAMP.gem, 7, 2);
b.camp(CAMP.gem, 2, 7);
b.camp(CAMP.gem, 7, 7);
b.camp(CAMP.gold, 10, 3);
b.camp(CAMP.gold, 3, 10);
b.camp(CAMP.wolf, 9, 9);
b.altar(12, 12);
fs.writeFileSync(new URL('../../maps/probe5/p5.map26a', import.meta.url), b.encode());
console.log('ok', b.numCamps());
