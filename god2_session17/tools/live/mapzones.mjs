#!/usr/bin/env node
// Static map value by zone, from a replay's camp list and round-1 spawns: groups (cardinally connected camps) classified by
// Chebyshev distance to team A's / team B's spawn centre: own(A) / mid (|dA - dB| <= M) / theirs. Gem and gold value per
// respawn cycle and HP per zone. One JSON line per replay.   node tools/live/mapzones.mjs M replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const M = +process.argv[2];
const GEMS = { wolf: 4, elk: 15, gem: 7, gold: 0, monolith: 200, golem: 36 }, GOLD = { wolf: 40, elk: 90, gem: 0, gold: 20, monolith: 300, golem: 160 };
const RESP = { wolf: 40, elk: 60, gem: 50, gold: 50, monolith: 150, golem: 80 };
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const camps = d.meta.camps || [];
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = camps.map((_, i) => i);
  const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = at.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par[find(c.index)] = find(j); }
  const groups = new Map();
  for (const c of camps) { const g = find(c.index); if (!groups.has(g)) groups.set(g, []); groups.get(g).push(c); }
  const s1 = d.rounds[1];
  const sp = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const z = { own: { n: 0, gems: 0, gold: 0, rate: 0, hp: 0 }, mid: { n: 0, gems: 0, gold: 0, rate: 0, hp: 0 }, theirs: { n: 0, gems: 0, gold: 0, rate: 0, hp: 0 } };
  for (const [g, cs] of groups) {
    const cx = cs.reduce((a, c) => a + c.x, 0) / cs.length, cy = cs.reduce((a, c) => a + c.y, 0) / cs.length;
    const dA = Math.max(Math.abs(cx - sp[0][0]), Math.abs(cy - sp[0][1])), dB = Math.max(Math.abs(cx - sp[1][0]), Math.abs(cy - sp[1][1]));
    const k = Math.abs(dA - dB) <= M ? 'mid' : dA < dB ? 'own' : 'theirs';
    const gems = cs.reduce((a, c) => a + (GEMS[c.type] || 0), 0), gold = cs.reduce((a, c) => a + (GOLD[c.type] || 0), 0);
    const resp = Math.max(...cs.map((c) => RESP[c.type] || 50));
    z[k].n++; z[k].gems += gems; z[k].gold += gold; z[k].rate += gems / resp; z[k].hp += cs.reduce((a, c) => a + c.hp, 0);
  }
  const tot = z.own.rate + z.mid.rate + z.theirs.rate;
  console.log(JSON.stringify({ file: file.split('/').pop(), W: d.meta.width, H: d.meta.height, midShare: +(z.mid.rate / tot).toFixed(2), z }));
}
