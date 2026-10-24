#!/usr/bin/env node
// Wasted farm capacity: for every camp group, the rounds it stands fully alive (every camp at full health, nobody hitting it) and the
// number of times it was captured, by which team. Groups are assigned to a zone relative to team 0 (O0 nearer team 0's spawn,
// O1 nearer team 1's, M within 4 of the midline). One JSON line per replay: per zone, groups, idle-alive rounds, captures by team.
//   CAMBC_CACHE=... node tools/live/grp_idle.mjs replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
for (const file of process.argv.slice(2)) {
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
  const spawn = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const zoneOf = (cs) => {
    const x = cs.reduce((a, c) => a + c.x, 0) / cs.length, y = cs.reduce((a, c) => a + c.y, 0) / cs.length;
    const d0 = Math.max(Math.abs(x - spawn[0][0]), Math.abs(y - spawn[0][1])), d1 = Math.max(Math.abs(x - spawn[1][0]), Math.abs(y - spawn[1][1]));
    return Math.abs(d0 - d1) <= 4 ? 'M' : d0 < d1 ? 'O0' : 'O1';
  };
  const maxHp = camps.map((c) => c.hp);
  const out = { file: file.split(/[\\/]/).pop(), final: d.meta.finalRound, zones: {} };
  const capOf = new Map();
  for (const e of d.events) if (e.k === 'CaptureGems' && e.at) {
    const i = at.get(e.at[0] * 1000 + e.at[1]);
    if (i === undefined) continue;
    const g = find(i);
    const key = `${g}:${e.r}:${e.team}`;
    if (capOf.has(key)) continue;
    capOf.set(key, { g, r: e.r, team: e.team, gems: e.gems });
  }
  for (const [g, cs] of groups) {
    const z = zoneOf(cs);
    const Z = out.zones[z] || (out.zones[z] = { groups: 0, idle: 0, damaged: 0, dead: 0, caps0: 0, caps1: 0, gems: 0 });
    Z.groups++;
    for (let r = 1; r < d.rounds.length; r++) {
      const s = d.rounds[r];
      if (!s || !s.campHp) continue;
      const hp = cs.map((c) => s.campHp[c.index]);
      if (cs.every((c, k) => hp[k] >= maxHp[c.index] && maxHp[c.index] > 0)) Z.idle++;
      else if (hp.every((h) => h <= 0)) Z.dead++;
      else Z.damaged++;
    }
  }
  for (const c of capOf.values()) {
    const z = zoneOf(groups.get(c.g));
    out.zones[z][c.team === 0 ? 'caps0' : 'caps1']++;
  }
  console.log(JSON.stringify(out));
}
