// Session 5 win-race probe map (31x31, rot180, 4 champions per team): 16 gem clusters per half, centre altar (15,15).
import fs from 'node:fs';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';
const E = await loadEngine();
const b = new Builder(E, 31, 31, SYM.rot180);
b.champs(4);
b.spawn(1, 1, 5, 5);
const cl = [[6,2],[9,2],[12,2],[12,5],  [2,6],[2,9],[2,12],[5,12],  [6,6],[9,6],[6,9],[9,9],  [12,8],[12,11],[8,12],[15,6]];
for (const [x, y] of cl) b.camp(CAMP.gem, x, y);
b.altar(15, 15);
fs.writeFileSync(new URL('../../maps/probe5/p6.map26a', import.meta.url), b.encode());
console.log('ok', b.numCamps());
