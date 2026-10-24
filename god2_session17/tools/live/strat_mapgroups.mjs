#!/usr/bin/env node
// Fix-up for tools/live/strat_mapgeo.mjs: a replay loaded through Game_FromReplayFileBytes lists only one side's camp groups, so
// rebuild the groups from the full camp list of a decoded game (tools/live/fightdump.mjs dumps: meta.camps, both sides) as
// cardinally connected components (the rules' camp groups), check them against the engine's one-side groups, and recompute the
// group-derived features.   node tools/live/strat_mapgroups.mjs mapgeo.jsonl DUMPDIR > mapgeo2.jsonl
import fs from 'node:fs';
import zlib from 'node:zlib';
const [geoPath, dumpDir] = process.argv.slice(2);
const GEMS = { wolf: 4, elk: 15, gem: 7, gold: 0, monolith: 200, golem: 36 };
const GOLD = { wolf: 40, elk: 90, gem: 0, gold: 20, monolith: 300, golem: 160 };
const RESP = { wolf: 40, elk: 60, gem: 50, gold: 50, monolith: 150, golem: 80 };
const HP = { wolf: 1350, elk: 2400, gem: 120, gold: 120, monolith: 20000, golem: 5000 };
const dumps = fs.readdirSync(dumpDir);
for (const line of fs.readFileSync(geoPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const g = JSON.parse(line);
  const f = dumps.find((x) => x.replace(/_[0-9a-f]{8}\.json\.gz$/, '') === g.map);
  if (!f) { process.stderr.write(`no dump for ${g.map}\n`); console.log(line); continue; }
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(`${dumpDir}/${f}`)));
  const camps = d.meta.camps.map((c) => ({ ...c, type: c.type === 5 ? 'golem' : c.type }));
  const W = g.W, H = g.H;
  const at = new Map(camps.map((c, k) => [c.x * 1000 + c.y, k]));
  const par = camps.map((_, k) => k);
  const find = (k) => (par[k] === k ? k : (par[k] = find(par[k])));
  for (const [k, c] of camps.entries()) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(k)] = find(j); }
  const comp = new Map();
  for (const [k] of camps.entries()) { const r = find(k); if (!comp.has(r)) comp.set(r, []); comp.get(r).push(camps[k]); }
  // check vs the engine's one-side groups
  let bad = 0;
  for (const eg of g.groups) {
    const ks = eg.camps.map((c) => at.get(c[0] * 1000 + c[1]));
    if (ks.some((k) => k === undefined)) { bad++; continue; }
    const r = find(ks[0]);
    if (ks.some((k) => find(k) !== r) || comp.get(r).length !== ks.length) bad++;
  }
  const pass = (x, y) => x >= 0 && y >= 0 && x < W && y < H && g.grid[y][x] !== '#' && g.grid[y][x] !== 'o' && g.grid[y][x] !== 'A';
  const dist = (arr, x, y) => {
    if (pass(x, y) && arr[y * W + x] >= 0) return arr[y * W + x];
    let best = 1e9; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const nx = x + dx, ny = y + dy; if (pass(nx, ny) && arr[ny * W + nx] >= 0) best = Math.min(best, arr[ny * W + nx] + 1); }
    return best >= 1e9 ? -1 : best;
  };
  const groups = [];
  for (const cs of comp.values()) {
    const n = cs.length;
    const cx = cs.reduce((a, c) => a + c.x, 0) / n, cy = cs.reduce((a, c) => a + c.y, 0) / n;
    const ga = Math.min(...cs.map((c) => { const v = dist(g.dA, c.x, c.y); return v < 0 ? 1e9 : v; }));
    const gb = Math.min(...cs.map((c) => { const v = dist(g.dB, c.x, c.y); return v < 0 ? 1e9 : v; }));
    groups.push({ i: groups.length, camps: cs.map((c) => [c.x, c.y, c.type, c.index]), cx: +cx.toFixed(1), cy: +cy.toFixed(1), dA: ga, dB: gb, f: +(ga / (ga + gb)).toFixed(3),
      gems: cs.reduce((a, c) => a + (GEMS[c.type] || 0), 0), gold: cs.reduce((a, c) => a + (GOLD[c.type] || 0), 0),
      resp: Math.max(...cs.map((c) => RESP[c.type] || 50)), hp: cs.reduce((a, c) => a + (HP[c.type] || 0), 0) });
  }
  const rate = (gs) => gs.reduce((a, x) => a + x.gems / x.resp, 0);
  const mids = groups.filter((x) => x.f > 0.4 && x.f < 0.6);
  const has = (x, t) => x.camps.some((c) => c[2] === t);
  Object.assign(g.feat, {
    groups: groups.length, midGroups: mids.length, midShare: +(rate(mids) / Math.max(1e-9, rate(groups))).toFixed(2), gemRate: +rate(groups).toFixed(2),
    mono: groups.filter((x) => has(x, 'monolith')).length, monoMid: mids.filter((x) => has(x, 'monolith')).length,
    golem: groups.filter((x) => has(x, 'golem')).length, golemMid: mids.filter((x) => has(x, 'golem')).length,
    elk: groups.filter((x) => has(x, 'elk')).length, heavyMid: mids.filter((x) => x.hp >= 2400).length,
    midGems: mids.reduce((a, x) => a + x.gems, 0), allGems: groups.reduce((a, x) => a + x.gems, 0),
    engineGroupMismatch: bad,
  });
  g.groups = groups;
  process.stderr.write(`${g.map}: camps ${camps.length} groups ${groups.length} (engine one-side ${g.groups.length}) mismatches ${bad}\n`);
  console.log(JSON.stringify(g));
}
