// Side-swapped copy of a map: identical terrain and camps, but team A spawns where team B did (and vice versa).
// Used to separate "team letter" effects (turn order, team-B tiebreak) from "geometry" effects (raster-order
// tie-breaks in our code or the engine) in mirror matches.  node tools/mapgen/swap_sides.mjs IN OUT [--transpose] [--keep]
// --transpose: also swap x and y (H <-> V symmetry); --keep: keep team A's spawn (only the transpose).
import fs from 'node:fs';
import { loadEngine, Builder } from './engine.mjs';
const args = process.argv.slice(2);
const [inp, outp] = args.filter((a) => !a.startsWith('--'));
const TR = args.includes('--transpose'), KEEP = args.includes('--keep');
const E = await loadEngine();
const { X, out, mem, chk } = E;
const buf = fs.readFileSync(inp);
const p = X.Engine_Malloc(buf.length);
new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
chk(X.Game_FromMapFileBytes(p, buf.length, out, 0), 'load');
const g = mem().getBigUint64(out, true);
chk(X.Game_GetBitboardMetadata(g, out), 'meta');
const w = mem().getInt32(out, true), h = mem().getInt32(out + 4, true);
chk(X.Game_GetSymmetry(g, out), 'sym'); const sym = mem().getInt32(out, true);
chk(X.Game_GetNumChampsPerTeam(g, out), 'n'); const champs = mem().getInt32(out, true);
chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
const sp = [0, 4, 8, 12].map((o) => mem().getInt32(out + o, true));
const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return mem().getUint8(out) !== 0; };
const mirror = (x, y) => sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y];
const T = (x, y) => TR ? [y, x] : [x, y];
const [W2, H2] = T(w, h);
const sym2 = TR && sym !== 2 ? 1 - sym : sym;
const b = new Builder(E, W2, H2, sym2);
b.champs(champs);
// mirrored spawn rectangle (max exclusive)
let [ax, ay] = KEEP ? [sp[0], sp[1]] : mirror(sp[0], sp[1]), [bx, by] = KEEP ? [sp[2] - 1, sp[3] - 1] : mirror(sp[2] - 1, sp[3] - 1);
[ax, ay] = T(ax, ay); [bx, by] = T(bx, by);
b.spawn(Math.min(ax, bx), Math.min(ay, by), Math.max(ax, bx) + 1, Math.max(ay, by) + 1);
const B0 = { wall: (x, y) => b.wall(...T(x, y)), hole: (x, y) => b.hole(...T(x, y)), bush: (x, y) => b.bush(...T(x, y)) };
const altars = [];
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
  if (tile('Game_GetWall', x, y)) B0.wall(x, y);
  else if (tile('Game_GetHole', x, y)) B0.hole(x, y);
  else if (tile('Game_GetAltar', x, y)) altars.push(T(x, y));
  else if (tile('Game_GetBush', x, y)) B0.bush(x, y);
}
for (const [x, y] of altars) { try { b.altar(x, y); } catch (e) { /* mirrored automatically */ } }
chk(X.Game_GetNumCamps(g, out), 'nc'); const nc = mem().getUint32(out, true);
for (let i = 0; i < nc; i++) {
  chk(X.Game_GetCampHandle(g, i, out), 'ch'); const hnd = mem().getBigUint64(out, true);
  chk(X.Game_GetCamp(g, hnd, out), 'camp');
  const t = mem().getInt32(out, true), x = mem().getInt32(out + 4, true), y = mem().getInt32(out + 8, true);
  const [mx, my] = KEEP ? [x, y] : mirror(x, y);
  b.camp(t, ...T(mx, my));
}
fs.writeFileSync(outp, b.encode());
console.log(`${outp}: ${w}x${h} sym ${sym} spawnA was ${sp}`);
