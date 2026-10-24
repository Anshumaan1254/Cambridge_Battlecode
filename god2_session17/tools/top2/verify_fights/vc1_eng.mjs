#!/usr/bin/env node
// Verify C1 (an_fights.md): engagements and fresh contacts, independent implementation over fightdump dumps.
// Engagement = champion-vs-champion hits clustered in time (gap <= GAP rounds) and space (victim within 10 of the cluster's
// last hit victim); kept when >= 3 hits or a death. Starter = team of the first hit's attacker (by step order q).
// Local state at the start = end of round r0-1, bodies alive within 8 (Chebyshev) of the first attacker or first victim;
// two variants: all bodies / excluding bodies standing on their own spawn (first attacker and victim always included).
// Deaths = Death events whose killing step is a hit of the cluster. Fresh contact = an S-O pair comes within 5 (was > 5),
// neither on its spawn, no champion hit within 10 tiles in the previous 8 rounds, no other contact within 10 tiles in the last
// 8 rounds; first = team of the first champion hit within 10 tiles in rounds r..r+4.
//   node vc1_eng.mjs games.json mapgeo.jsonl SHARD NSHARD > out.jsonl
import { loadGeo, loadGame, readGames, cheb } from './vlib.mjs';
const [gf, geof, shard, nsh] = process.argv.slice(2);
const geo = loadGeo(geof);
const games = readGames(gf).filter((_, i) => i % +nsh === +shard);
const GAP = 6;
for (const row of games) {
  const G = loadGame(row, geo);
  const { nb, team } = G;
  // ---- engagements
  const clusters = [];
  const active = [];
  for (const h of G.hits) {
    const r = h.r;
    const pr = G.alive(r, h.v) ? r : r - 1; // a killed victim's end-of-round tile is not its death tile
    const vx = G.x(pr, h.v), vy = G.y(pr, h.v);
    let best = null;
    for (const c of active) {
      if (r - c.lastR > GAP) continue;
      if (cheb(vx, vy, c.lx, c.ly) > 10) continue;
      if (!best || c.lastR > best.lastR) best = c;
    }
    if (!best) { best = { hits: [], lastR: r, lx: vx, ly: vy, r0: r }; clusters.push(best); active.push(best); }
    best.hits.push(h); best.lastR = r; best.lx = vx; best.ly = vy;
    // prune
    for (let i = active.length - 1; i >= 0; i--) if (r - active[i].lastR > GAP) active.splice(i, 1);
  }
  const deathByQ = new Map();
  for (const e of G.deaths) deathByQ.set(e.q + ':' + e.who, e);
  const engs = [];
  for (const c of clusters) {
    const deaths = [0, 0];
    const dset = new Set();
    for (const h of c.hits) { const e = deathByQ.get(h.q + ':' + h.v); if (e && !dset.has(h.q + ':' + h.v)) { dset.add(h.q + ':' + h.v); deaths[team[h.v]]++; } }
    if (c.hits.length < 3 && deaths[0] + deaths[1] === 0) continue;
    const f = c.hits[0], r0 = f.r, rp = Math.max(0, r0 - 1);
    const ax = G.x(rp, f.a), ay = G.y(rp, f.a), vx = G.x(rp, f.v), vy = G.y(rp, f.v);
    const side = [0, 1].map(() => ({ n: 0, mx: 0, hp: 0, nX: 0, mxX: 0, hpX: 0 }));
    for (let b = 0; b < nb; b++) {
      if (!G.alive(rp, b)) continue;
      const x = G.x(rp, b), y = G.y(rp, b);
      const near = cheb(x, y, ax, ay) <= 8 || cheb(x, y, vx, vy) <= 8 || b === f.a || b === f.v;
      if (!near) continue;
      const t = team[b], s = side[t];
      s.n++; s.mx += G.mhp(rp, b); s.hp += G.hp(rp, b);
      if (b === f.a || b === f.v || !G.onSpawn(rp, b)) { s.nX++; s.mxX += G.mhp(rp, b); s.hpX += G.hp(rp, b); }
    }
    // damage per side in first 3 rounds and total
    const d3 = [0, 0], dt = [0, 0], nh = [0, 0], cast3 = [0, 0];
    for (const h of c.hits) { const t = team[h.a]; dt[t] += h.amt; nh[t]++; if (h.r <= r0 + 2) { d3[t] += h.amt; if (h.kind === 6) cast3[t]++; } }
    const S = G.S, O = G.O;
    engs.push({
      r0, r1: c.lastR, st: team[f.a] === S ? 1 : 0, fk: f.kind, n: c.hits.length,
      dS: deaths[S], dO: deaths[O],
      nS: side[S].n, nO: side[O].n, mS: side[S].mx, mO: side[O].mx, hS: side[S].hp, hO: side[O].hp,
      nSx: side[S].nX, nOx: side[O].nX, mSx: side[S].mxX, mOx: side[O].mxX, hSx: side[S].hpX, hOx: side[O].hpX,
      d3S: d3[S], d3O: d3[O], dtS: dt[S], dtO: dt[O],
    });
  }
  // ---- fresh contacts
  const contacts = [];
  const hitPosBy = [];
  const P = (r, b) => (G.alive(r, b) || r === 0) ? [G.x(r, b), G.y(r, b)] : [G.x(r - 1, b), G.y(r - 1, b)];
  for (let r = 0; r < G.NR; r++) hitPosBy.push(G.hitsBy[r].map((h) => [...P(r, h.v), ...P(r, h.a), team[h.a], h.q]));
  for (let r = 2; r <= G.last; r++) {
    for (const s of G.sb) for (const o of G.ob) {
      if (!G.alive(r, s) || !G.alive(r, o) || !G.alive(r - 1, s) || !G.alive(r - 1, o)) continue;
      if (G.onSpawn(r, s) || G.onSpawn(r, o)) continue;
      if (G.dist(r, s, o) > 5 || G.dist(r - 1, s, o) <= 5) continue;
      const cx = (G.x(r, s) + G.x(r, o)) / 2, cy = (G.y(r, s) + G.y(r, o)) / 2;
      let dirty = false;
      for (let rr = Math.max(1, r - 8); rr < r && !dirty; rr++) for (const p of hitPosBy[rr]) if (cheb(p[0], p[1], cx, cy) <= 10 || cheb(p[2], p[3], cx, cy) <= 10) { dirty = true; break; }
      if (dirty) continue;
      if (contacts.some((c) => r - c.r <= 8 && cheb(c.cx, c.cy, cx, cy) <= 10)) continue;
      // first hit within 10 tiles in rounds r..r+4
      let first = -1;
      for (let rr = r; rr <= Math.min(G.last, r + 4) && first < 0; rr++) for (const p of hitPosBy[rr]) if (cheb(p[0], p[1], cx, cy) <= 10 || cheb(p[2], p[3], cx, cy) <= 10) { first = p[4]; break; }
      // local max-health ratio within 8 of the contact centre (excluding bodies on own spawn)
      let mS = 0, mO = 0;
      for (let b = 0; b < nb; b++) { if (!G.alive(r, b) || G.onSpawn(r, b)) continue; if (cheb(G.x(r, b), G.y(r, b), cx, cy) <= 8) { if (team[b] === G.S) mS += G.mhp(r, b); else mO += G.mhp(r, b); } }
      contacts.push({ r, cx, cy, first: first < 0 ? -1 : (first === G.S ? 1 : 0), ratio: mO > 0 ? mS / mO : 99 });
    }
  }
  console.log(JSON.stringify({ key: row.key, map: row.map, match: row.match, dump: row.dump, swon: row.swon, ssize: row.ssize, osize: row.osize,
    final: G.final, engs, contacts: contacts.map((c) => [c.r, c.first, +c.ratio.toFixed(3)]) }));
}
