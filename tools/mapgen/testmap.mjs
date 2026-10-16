import fs from 'node:fs';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';
const E = await loadEngine();
const b = new Builder(E, 30, 30, SYM.rot180);
b.champs(5);
b.spawn(1, 1, 4, 4);       // tiles 1..3
b.camp(CAMP.gem, 9, 2);    // gem cluster
b.camp(CAMP.wolf, 12, 9);  // wolf
b.camp(CAMP.elk, 3, 12);   // elk
b.camp(CAMP.gold, 8, 8);   // gold cluster
b.altar(6, 2);             // altar near spawn
b.camp(CAMP.monolith, 14, 13);
fs.writeFileSync(new URL('../../maps/zz_test.map26a', import.meta.url), b.encode());
console.log('ok');
