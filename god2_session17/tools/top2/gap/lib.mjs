// gap_g8 helpers: load a cached decode (tools/top2/gap/deccache.mjs) or a fight dump, spawn centres, zones, camp groups.
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

export const DEC = 'C:/battlecode/cache/gap_g8/dec';
export const DUMP = 'C:/battlecode/cache/t2dump/s0';
export const SIDES = 'C:/battlecode/cache/gap_g8/sides.json';
export const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
export const gameName = (f) => path.basename(f).replace(/\.(json\.gz|repl26a)$/, '');

export function loadDec(f) { return JSON.parse(zlib.gunzipSync(fs.readFileSync(f))); }
export function loadSides() { return JSON.parse(fs.readFileSync(SIDES, 'utf8')); }

// spawn centre per team from round 1 positions; zone of a tile relative to team t: O own half, M middle band (|dA-dB| <= 4), T their half
export function spawns(d) {
  const s1 = d.rounds[1];
  return [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
}
export function spawnTiles(d) {
  const s1 = d.rounds[1];
  return [0, 1].map((t) => s1.ch.filter((c) => c[1] === t).map((c) => [c[3], c[4]]));
}
export function zoneFn(sp) {
  return (team, x, y) => {
    const da = cheb([x, y], sp[team]), db = cheb([x, y], sp[1 - team]);
    return Math.abs(da - db) <= 4 ? 'M' : da < db ? 'O' : 'T';
  };
}
// camp groups = cardinally connected camp spawn tiles (as the engine defines a group)
export function groups(d) {
  const camps = d.meta.camps || [];
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = camps.map((_, i) => i);
  const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(c.index)] = find(j); }
  const G = new Map();
  for (const c of camps) { const g = find(c.index); if (!G.has(g)) G.set(g, { id: g, camps: [] }); G.get(g).camps.push(c); }
  for (const g of G.values()) {
    g.x = g.camps.reduce((a, c) => a + c.x, 0) / g.camps.length; g.y = g.camps.reduce((a, c) => a + c.y, 0) / g.camps.length;
    g.mix = {}; for (const c of g.camps) g.mix[campKind(c)] = (g.mix[campKind(c)] || 0) + 1;
    g.kind = g.mix.monolith ? 'monolith' : g.mix.golem ? 'golem' : g.mix.elk ? 'elk' : g.mix.wolf ? 'wolf' : 'cluster';
    g.hp = g.camps.reduce((a, c) => a + c.hp, 0);
  }
  const gOf = (x, y) => { const i = at.get(x * 1000 + y); return i === undefined ? -1 : find(i); };
  return { G, gOf, campAt: at };
}
// camp kind by max health (the decoder's type names predate the golem): wolf 1350, elk 2400, golem 5000, clusters 120, monolith 20000
export function campKind(c) {
  const h = c.hp;
  if (h >= 15000) return 'monolith';
  if (h >= 4000) return 'golem';
  if (h >= 2000) return 'elk';
  if (h >= 1000) return 'wolf';
  return c.type === 'gold' ? 'goldc' : 'gemc';
}
export function phaseOf(r) { return r < 300 ? 0 : r < 600 ? 1 : r < 1000 ? 2 : 3; }
export const PHASES = ['r1-299', 'r300-599', 'r600-999', 'r1000+'];
