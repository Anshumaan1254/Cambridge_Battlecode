#!/usr/bin/env node
// Why camp work stops: per body, hitting sessions on one camp group (hits with gaps <= 3 rounds). A session ends "finished" when the
// group is dead within 3 rounds of the last hit, else "left". For left sessions: enemy champion within 8 of the body at the last hit,
// body health fraction, carried gems, and what it does over the next 10 rounds (fight = hits a champion, other = hits another group,
// dead, walk, idle) and whether it came back to the group within 30 rounds. One JSON line per replay with per-team counters.
//   CAMBC_CACHE=... node tools/live/abandon_why.mjs replay...
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
  const members = new Map();
  for (const c of camps) { const g = find(c.index); if (!members.has(g)) members.set(g, []); members.get(g).push(c.index); }
  const hits = new Map(); // body -> [{r, g}] camp hits;  champHits: body -> Set(r)
  const champHits = new Map();
  for (const e of d.events) {
    if ((e.k !== 'Attack' && e.k !== 'Cast ability') || e.who === undefined || !e.to) continue;
    const i = at.get(e.to[0] * 1000 + e.to[1]);
    if (i !== undefined) { if (!hits.has(e.who)) hits.set(e.who, []); hits.get(e.who).push({ r: e.r, g: find(i) }); }
    else { if (!champHits.has(e.who)) champHits.set(e.who, new Set()); champHits.get(e.who).add(e.r); }
  }
  const deadAt = (g, r) => { const s = d.rounds[Math.min(r, d.rounds.length - 1)]; return s && s.campHp && members.get(g).every((i) => s.campHp[i] <= 0); };
  const out = { file: file.split(/[\\/]/).pop(), teams: { 0: {}, 1: {} } };
  const inc = (t, k) => { out.teams[t][k] = (out.teams[t][k] || 0) + 1; };
  for (const [b, hs] of hits) {
    const team = d.meta.bodies[b].team;
    let i = 0;
    while (i < hs.length) {
      let j = i;
      while (j + 1 < hs.length && hs[j + 1].g === hs[i].g && hs[j + 1].r - hs[j].r <= 3) j++;
      const g = hs[i].g, r1 = hs[j].r;
      inc(team, 'sessions');
      let finished = false;
      for (let r = r1; r <= r1 + 3; r++) if (deadAt(g, r)) finished = true;
      if (finished) { inc(team, 'finished'); i = j + 1; continue; }
      inc(team, 'left');
      const s = d.rounds[r1];
      const me = s && s.ch.find((c) => c[0] === b);
      if (me) {
        const enemy = s.ch.some((c) => c[7] && c[1] !== team && Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4])) <= 8);
        inc(team, enemy ? 'left_enemy8' : 'left_noenemy');
        if (me[5] < 0.4 * me[6]) inc(team, 'left_lowhp');
        if (me[8] >= 40) inc(team, 'left_bag40');
        // next 10 rounds
        let nxt = 'idle';
        for (let r = r1 + 1; r <= r1 + 10 && r < d.rounds.length; r++) {
          const c = d.rounds[r].ch.find((q) => q[0] === b);
          if (!c || !c[7]) { nxt = 'dead'; break; }
          if (champHits.get(b)?.has(r)) { nxt = 'fight'; break; }
          if (hs.some((h) => h.r === r && h.g !== g)) { nxt = 'other_group'; break; }
          const p = d.rounds[r - 1].ch.find((q) => q[0] === b);
          if (p && (p[3] !== c[3] || p[4] !== c[4])) nxt = 'walk';
        }
        inc(team, 'next_' + nxt);
        if (hs.some((h) => h.g === g && h.r > r1 && h.r <= r1 + 30)) inc(team, 'came_back30');
      }
      i = j + 1;
    }
  }
  console.log(JSON.stringify(out));
}
