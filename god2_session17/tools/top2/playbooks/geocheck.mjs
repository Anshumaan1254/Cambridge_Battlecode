#!/usr/bin/env node
// Check that the cached map geometry (C:/battlecode/cache/an_strategy/mapgeo2.jsonl: grid, BFS distances dA/dB from spawn A/B,
// altars, camp groups) still matches the camps and spawns in the t2 fight dumps (one dump per map), and print camp types per map.
//   node tools/top2/playbooks/geocheck.mjs
import fs from 'node:fs';
import zlib from 'node:zlib';
const geo = new Map(fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => { const g = JSON.parse(l); return [g.map, g]; }));
const seen = new Set();
for (const key of ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']) {
  const dir = `C:/battlecode/cache/t2dump/${key}`;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json.gz'))) {
    const map = f.replace(/_[0-9a-f]{8}\.json\.gz$/, '');
    if (seen.has(map)) continue;
    seen.add(map);
    const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(`${dir}/${f}`)));
    const g = geo.get(map);
    const ct = {};
    for (const c of d.meta.camps) ct[c.type] = (ct[c.type] || 0) + 1;
    const r0 = d.R[0][3];
    const sp = [0, 1].map((t) => { const b = r0.filter((c) => d.meta.bodies[c[0]].team === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length].map((v) => +v.toFixed(1)); });
    let match = 'nogeo';
    if (g) {
      const gs = new Set(g.groups.flatMap((x) => x.camps.map((c) => c[0] * 1000 + c[1])));
      const ds = new Set(d.meta.camps.map((c) => c.x * 1000 + c.y));
      const miss = [...ds].filter((k) => !gs.has(k)).length, extra = [...gs].filter((k) => !ds.has(k)).length;
      match = `miss ${miss} extra ${extra} W ${g.W}x${g.H} vs ${d.meta.width}x${d.meta.height} spawnA ${JSON.stringify(g.spawnA)} spawnB ${JSON.stringify(g.spawnB)}`;
    }
    console.log(map, d.meta.bodies.length / 2, JSON.stringify(ct), 'spawns', JSON.stringify(sp), match);
  }
}
