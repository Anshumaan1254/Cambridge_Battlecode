// Patch-3.0-style copy of a map (session 13): the Oct 20 patch cut camp rewards (wolf 4 gems, elk 15, gem cluster 7) and said the
// map makers will "alter the value of camp groups through the use of Gem and Gold clusters". The new official pool could not be
// pulled here, so this adds gem clusters next to the attacking camps (and next to gem clusters) of an existing map, joining their
// groups, and optionally a golem per side. Terrain, spawns, altars and the other camps are kept.
//   node tools/mapgen/patch30.mjs IN OUT [--wolf N] [--elk N] [--gem N] [--golem]
// Defaults: 2 gem clusters per wolf, 2 per elk, 1 per gem cluster; no golem.
import fs from 'node:fs';
import { loadEngine, Builder, CAMP } from './engine.mjs';
const args = process.argv.slice(2);
const [inp, outp] = args.filter((a) => !a.startsWith('--') && isNaN(Number(a)));
const num = (k, d) => { const i = args.indexOf(k); return i >= 0 ? Number(args[i + 1]) : d; };
const PER = { 0: num('--wolf', 2), 1: num('--elk', 2), 2: num('--gem', 1) };
const GOLEM = args.includes('--golem');
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
const b = new Builder(E, w, h, sym);
b.champs(champs);
b.spawn(sp[0], sp[1], sp[2], sp[3]);
const blocked = new Set();
const key = (x, y) => y * w + x;
const altars = [];
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
  if (tile('Game_GetWall', x, y)) { b.wall(x, y); blocked.add(key(x, y)); }
  else if (tile('Game_GetHole', x, y)) { b.hole(x, y); blocked.add(key(x, y)); }
  else if (tile('Game_GetAltar', x, y)) { altars.push([x, y]); blocked.add(key(x, y)); }
  else if (tile('Game_GetBush', x, y)) { b.bush(x, y); blocked.add(key(x, y)); }
}
for (const [x, y] of altars) { try { b.altar(x, y); } catch (e) { /* mirrored automatically */ } }
// spawn regions of both teams stay free
for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) { blocked.add(key(x, y)); const [mx, my] = mirror(x, y); blocked.add(key(mx, my)); }
chk(X.Game_GetNumCamps(g, out), 'nc'); const nc = mem().getUint32(out, true);
const camps = [];
for (let i = 0; i < nc; i++) {
  chk(X.Game_GetCampHandle(g, i, out), 'ch'); const hnd = mem().getBigUint64(out, true);
  chk(X.Game_GetCamp(g, hnd, out), 'camp');
  const t = mem().getInt32(out, true), x = mem().getInt32(out + 4, true), y = mem().getInt32(out + 8, true);
  camps.push([t, x, y]);
  blocked.add(key(x, y));
}
for (const [t, x, y] of camps) { try { b.camp(t, x, y); } catch (e) { /* the mirrored copy of a camp already added */ } }
// one canonical half: a camp whose mirror image sorts before it is added by the builder's mirroring
const canon = (x, y) => { const [mx, my] = mirror(x, y); return y < my || (y === my && x <= mx); };
let added = 0;
const tryAdd = (type, x, y) => {
  if (x < 0 || y < 0 || x >= w || y >= h || blocked.has(key(x, y))) return false;
  const [mx, my] = mirror(x, y);
  if (blocked.has(key(mx, my))) return false;
  try { b.camp(type, x, y); } catch (e) { return false; }
  blocked.add(key(x, y)); blocked.add(key(mx, my)); added++;
  return true;
};
for (const [t, x, y] of camps) {
  if (!canon(x, y) || !(t in PER)) continue;
  let n = PER[t];
  for (let r = 1; r <= 2 && n > 0; r++)
    for (let dy = -r; dy <= r && n > 0; dy++)
      for (let dx = -r; dx <= r && n > 0; dx++)
        if (Math.max(Math.abs(dx), Math.abs(dy)) === r && tryAdd(CAMP.gem, x + dx, y + dy)) n--;
}
if (GOLEM) {
  // one golem per side halfway between the spawn and the map centre, on the first free tile found
  const cx = (sp[0] + sp[2]) / 2, cy = (sp[1] + sp[3]) / 2;
  const gx = Math.round((cx + w / 2) / 2), gy = Math.round((cy + h / 2) / 2);
  let done = false;
  for (let r = 0; r <= 6 && !done; r++)
    for (let dy = -r; dy <= r && !done; dy++)
      for (let dx = -r; dx <= r && !done; dx++)
        done = tryAdd(5, gx + dx, gy + dy); // camp type 5 = golem (engine v1.0)
}
fs.writeFileSync(outp, b.encode());
console.log(`${outp}: ${w}x${h} champs ${champs}, ${camps.length} camps + ${added} added`);
