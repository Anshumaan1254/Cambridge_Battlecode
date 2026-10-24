#!/usr/bin/env node
// Farming cycle phases per camp group: respawned (full) -> first damage (wait), first damage -> all camps dead (kill), all dead ->
// reward captured (capture), captured -> full again (respawn; anything above the group's timer is a blocked spawn tile). Each
// completed cycle is attributed to the capturing team and the group's zone relative to that team (O own half, M middle, T their half).
// One JSON line per replay: cycles: [{team, zone, wait, kill, cap, respawn}] (respawn null for the last cycle).
//   CAMBC_CACHE=... node tools/live/grp_cycles.mjs replay...
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
  const zoneFor = (team, cs) => {
    const x = cs.reduce((a, c) => a + c.x, 0) / cs.length, y = cs.reduce((a, c) => a + c.y, 0) / cs.length;
    const da = Math.max(Math.abs(x - spawn[team][0]), Math.abs(y - spawn[team][1])), db = Math.max(Math.abs(x - spawn[1 - team][0]), Math.abs(y - spawn[1 - team][1]));
    return Math.abs(da - db) <= 4 ? 'M' : da < db ? 'O' : 'T';
  };
  const capByGroup = new Map();
  for (const e of d.events) if (e.k === 'CaptureGems' && e.at) {
    const i = at.get(e.at[0] * 1000 + e.at[1]);
    if (i === undefined) continue;
    const g = find(i);
    if (!capByGroup.has(g)) capByGroup.set(g, []);
    const L = capByGroup.get(g);
    if (!L.some((x) => x.r === e.r)) L.push({ r: e.r, team: e.team });
  }
  const cycles = [];
  for (const [g, cs] of groups) {
    const maxHp = cs.map((c) => c.hp);
    const caps = (capByGroup.get(g) || []).sort((a, b) => a.r - b.r);
    let state = 'full', tFull = 1, tHit = null, tDead = null, ci = 0, pending = null;
    for (let r = 1; r < d.rounds.length; r++) {
      const s = d.rounds[r];
      if (!s || !s.campHp) continue;
      const hp = cs.map((c) => s.campHp[c.index]);
      const full = hp.every((h, k) => h >= maxHp[k] && maxHp[k] > 0);
      const dead = hp.every((h) => h <= 0);
      if (state === 'full' && !full) { state = 'hit'; tHit = r; }
      if (state === 'hit' && full) { state = 'full'; tFull = r; tHit = null; } // healed back (abandoned)
      if (state === 'hit' && dead) { state = 'dead'; tDead = r; }
      if (state === 'dead' && ci < caps.length && caps[ci].r <= r) {
        pending = { team: caps[ci].team, zone: zoneFor(caps[ci].team, cs), wait: tHit - tFull, kill: tDead - tHit, cap: caps[ci].r - tDead, respawn: null, tCap: caps[ci].r };
        ci++;
        state = 'respawning';
      }
      if (state === 'respawning' && full) { pending.respawn = r - pending.tCap; delete pending.tCap; cycles.push(pending); pending = null; state = 'full'; tFull = r; }
    }
    if (pending) { delete pending.tCap; cycles.push(pending); }
  }
  console.log(JSON.stringify({ file: file.split(/[\\/]/).pop(), cycles }));
}
