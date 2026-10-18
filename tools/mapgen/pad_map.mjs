// Resized copy of a map: the same terrain, camps, altars and spawns, framed by wall rows / columns, so the map plays
// the same but has a new size. Tests code that recognises a map by its size (official_map(), the stampede ring and
// contest plan gates) the way a changed map pool would.
//   node tools/mapgen/pad_map.mjs IN OUT [--padx N] [--pady M]   (default 2 and 2; both sides, so the symmetry holds)
import fs from 'node:fs';
import { loadEngine, Builder } from './engine.mjs';
const args = process.argv.slice(2);
const [inp, outp] = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--')));
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? Number(args[i + 1]) : d; };
const PX = opt('--padx', 2), PY = opt('--pady', 2);
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
const W2 = w + 2 * PX, H2 = h + 2 * PY;
if (W2 > 100 || H2 > 100) throw new Error(`${inp}: ${W2}x${H2} is over 100`);
const b = new Builder(E, W2, H2, sym);
b.champs(champs);
b.spawn(sp[0] + PX, sp[1] + PY, sp[2] + PX, sp[3] + PY);
for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++)
	if (x < PX || y < PY || x >= w + PX || y >= h + PY) b.wall(x, y);
const altars = [];
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
	if (tile('Game_GetWall', x, y)) b.wall(x + PX, y + PY);
	else if (tile('Game_GetHole', x, y)) b.hole(x + PX, y + PY);
	else if (tile('Game_GetAltar', x, y)) altars.push([x + PX, y + PY]);
	else if (tile('Game_GetBush', x, y)) b.bush(x + PX, y + PY);
}
for (const [x, y] of altars) { try { b.altar(x, y); } catch (e) { /* mirrored automatically */ } }
chk(X.Game_GetNumCamps(g, out), 'nc'); const nc = mem().getUint32(out, true);
for (let i = 0; i < nc; i++) {
	chk(X.Game_GetCampHandle(g, i, out), 'ch'); const hnd = mem().getBigUint64(out, true);
	chk(X.Game_GetCamp(g, hnd, out), 'camp');
	const t = mem().getInt32(out, true), x = mem().getInt32(out + 4, true), y = mem().getInt32(out + 8, true);
	b.camp(t, x + PX, y + PY);
}
fs.writeFileSync(outp, b.encode());
console.log(`${outp}: ${w}x${h} -> ${W2}x${H2} sym ${sym}, ${nc} camps`);
