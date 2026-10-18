// usage: node tools/econ/cycles.mjs [--groups] [--team T] FILE.repl26a...   (agent econ, session 7)
// Camp-group farming cycles from a replay, both teams: for every capture, the group's cycle split into
//   idle  = first damage - available (round 1, or the round it respawned)
//   clear = all camps dead - first damage
//   lag   = capture - all dead
// and who captured. Groups = camps joined at Chebyshev distance 1. Summary per team: captures, gems, mean idle/clear/lag,
// share of captures on gem groups, mean bodies that hit the group during the clear (from Attack events).
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const argv = process.argv.slice(2);
const showGroups = argv.includes('--groups');
const ti = argv.indexOf('--team');
const files = argv.filter((a, i) => !a.startsWith('--') && !(ti >= 0 && i === ti + 1));
const tot = [{}, {}];
for (const f of files) {
  const d = await decode(fs.readFileSync(f));
  const camps = d.meta.camps;
  const par = camps.map((_, i) => i);
  const find = (i) => (par[i] === i ? i : (par[i] = find(par[i])));
  for (let i = 0; i < camps.length; ++i) for (let j = i + 1; j < camps.length; ++j)
    if (Math.max(Math.abs(camps[i].x - camps[j].x), Math.abs(camps[i].y - camps[j].y)) <= 1) par[find(i)] = find(j);
  const groups = new Map();
  camps.forEach((c, i) => { const r = find(i); if (!groups.has(r)) groups.set(r, []); groups.get(r).push(i); });
  const G = [...groups.values()];
  const tileG = new Map();
  G.forEach((g, gi) => g.forEach((i) => tileG.set(camps[i].x + ',' + camps[i].y, gi)));
  const maxhp = camps.map((c, i) => Math.max(...d.rounds.map((s) => s.campHp[i] || 0)));
  // per round group state
  const st = G.map(() => ({ avail: 1, hit: -1, dead: -1, cyc: [], hitters: new Set() }));
  const caps = d.events.filter((e) => e.k === 'CaptureGems');
  const atk = d.events.filter((e) => e.k === 'Attack' || e.k === 'Cast ability');
  const atkBy = new Map();
  for (const e of atk) if (e.to) { const g = tileG.get(e.to[0] + ',' + e.to[1]); if (g !== undefined) { const k = e.r + ':' + g; if (!atkBy.has(k)) atkBy.set(k, new Set()); atkBy.get(k).add(e.team + ':' + e.who); } }
  // A capture-recall lands the reward on spawn: attribute it to the last group tile the champion stood on.
  const lastG = new Map(), capG = new Map();
  { let ci = 0; const cs = [...caps].sort((a, b) => a.r - b.r);
    for (const s of d.rounds) {
      while (ci < cs.length && cs[ci].r <= s.r) { const e = cs[ci++]; let g = tileG.get(e.at[0] + ',' + e.at[1]); if (g === undefined) g = lastG.get(e.who); if (g !== undefined) capG.set(e, g); }
      for (const c of s.ch) { const g = tileG.get(c[3] + ',' + c[4]); if (g !== undefined && c[7]) lastG.set(c[0], g); }
    } }
  const capBy = new Map();
  for (const e of caps) { const g = capG.get(e); if (g === undefined) continue; const k = e.r + ':' + g; if (!capBy.has(k)) capBy.set(k, []); capBy.get(k).push(e); }
  let prevAlive = G.map(() => true);
  for (const s of d.rounds) {
    G.forEach((g, gi) => {
      const S = st[gi];
      const hp = g.map((i) => s.campHp[i]);
      const allDead = hp.every((h) => h <= 0);
      const anyDmg = g.some((i) => s.campHp[i] < maxhp[i]);
      const full = g.every((i) => s.campHp[i] >= maxhp[i]);
      if (!prevAlive[gi] && !allDead) { S.avail = s.r; S.hit = -1; S.dead = -1; S.taken = false; S.hitters = new Set(); }
      if (S.hit < 0 && (anyDmg || !full) && !S.taken) S.hit = s.r;
      const a = atkBy.get(s.r + ':' + gi); if (a && S.dead < 0) for (const x of a) S.hitters.add(x);
      if (allDead && S.dead === -1) { S.dead = s.r; if (S.hit < 0) S.hit = s.r; }
      const c = capBy.get(s.r + ':' + gi);
      if (c && S.dead >= 0 && !S.taken) {
        const gems = c.reduce((t, e) => t + e.gems, 0);
        const teams = [...new Set(c.map((e) => e.team))];
        const hitTeams = [0, 1].map((t) => [...S.hitters].filter((h) => +h.split(':')[0] === t).length);
        S.cyc.push({ r: s.r, team: teams.join('+'), gems, idle: S.hit - S.avail, clear: S.dead - S.hit, lag: s.r - S.dead, split: c.length, who: c.map((e) => e.champ).join('+'), bodies: hitTeams });
        S.taken = true; // reward taken: wait for respawn
      }
      prevAlive[gi] = !allDead;
    });
  }
  const name = f.split('/').pop().replace(/\.repl26a$/, '');
  console.log(`== ${name} r${d.meta.finalRound} banked ${d.meta.submitted.join('-')}`);
  const per = [{ n: 0, gems: 0, idle: 0, clear: 0, lag: 0, b: 0 }, { n: 0, gems: 0, idle: 0, clear: 0, lag: 0, b: 0 }];
  G.forEach((g, gi) => {
    const S = st[gi];
    if (!S.cyc.length) return;
    const c0 = camps[g[0]];
    if (showGroups) console.log(`  g${gi} ${g.map((i) => camps[i].type[0]).join('')}@${c0.x},${c0.y}: ` + S.cyc.map((c) => `r${c.r}:${c.team}${c.split > 1 ? 'x' + c.split : ''}:${c.gems} i${c.idle}/c${c.clear}/l${c.lag} b${c.bodies.join('/')} ${c.who}`).join('  '));
    for (const c of S.cyc) for (const t of String(c.team).split('+').map(Number)) {
      const P = per[t]; P.n++; P.gems += c.gems / String(c.team).split('+').length; P.idle += c.idle; P.clear += c.clear; P.lag += c.lag; P.b += c.bodies[t];
      const T = tot[t]; T.n = (T.n || 0) + 1; T.gems = (T.gems || 0) + c.gems; T.idle = (T.idle || 0) + c.idle; T.clear = (T.clear || 0) + c.clear; T.lag = (T.lag || 0) + c.lag; T.b = (T.b || 0) + c.bodies[t];
    }
  });
  per.forEach((P, t) => { if (P.n && (ti < 0 || +argv[ti + 1] === t)) console.log(`  team ${t}: caps ${P.n} gems ${P.gems.toFixed(0)}  idle ${(P.idle / P.n).toFixed(1)} clear ${(P.clear / P.n).toFixed(1)} lag ${(P.lag / P.n).toFixed(1)} hitters ${(P.b / P.n).toFixed(2)}`); });
}
if (files.length > 1) tot.forEach((T, t) => { if (T.n) console.log(`TOTAL team ${t}: caps ${T.n} gems ${T.gems}  idle ${(T.idle / T.n).toFixed(1)} clear ${(T.clear / T.n).toFixed(1)} lag ${(T.lag / T.n).toFixed(1)} hitters ${(T.b / T.n).toFixed(2)}`); });
