#!/usr/bin/env node
// Verify C3 / C4 / C7 (an_fights.md), independent implementation over fightdump dumps. One JSON line per game with:
//  dec[]:  every 3rd round, every alive body off its spawn whose nearest enemy (alive, off its own spawn) is within 4:
//          [s, r, hpFrac, maxHp, d0, maxRatio8, curRatio8, weakestEnemyHpFrac6, act, died10, ownKills10, localNet10, recallActive]
//          act (next 3 rounds, first match): fight / recall (committed: not self-cancelled) / bank / dead / farm / leave / toward / hold
//  low[]:  health crosses below 35% off spawn: [s, r, d0 (nearest enemy), act (next 5 rounds), died15, maxRatio8, curRatio8, hpFrac]
//  rec[]:  every Recall event off spawn: [s, r, hpFrac, d0, outcome, hitByEnemy, ownTeamSpam, committedIdle]
//          outcome: done (teleported to spawn within 6 rounds) / killed / interrupted (enemy hit or stun first) / cancel (own cancel
//          first) / other; committedIdle = no own action in the next round (the analyst's Pantheon rule)
//  chase[]: A (chaser) and V within 3 rounds of a hit between them; V steps away from A and A steps after it; continues while A
//          closes or hits V; ends after 2 rounds without that, on V's death, A's death, distance > 10 or V on its spawn.
//          [s (chaser), aType, vHpFrac0, len, kill, chaserDiedDuring, chaserDied10After, startR]
//   node vc_dec.mjs games.json mapgeo.jsonl SHARD NSHARD > out.jsonl
import { loadGeo, loadGame, readGames, cheb } from './vlib.mjs';
const [gf, geof, shard, nsh] = process.argv.slice(2);
const geo = loadGeo(geof);
const games = readGames(gf).filter((_, i) => i % +nsh === +shard);
for (const row of games) {
  const G = loadGame(row, geo);
  const { nb, team, type, NR } = G;
  const S = G.S;
  const arr = (T) => Array.from({ length: nb }, () => new T(NR + 16));
  const dealt = arr(Float32Array), taken = arr(Float32Array), campHit = arr(Uint8Array), capR = arr(Uint8Array), subR = arr(Uint8Array);
  const recStart = arr(Uint8Array), kills = arr(Uint8Array), dead = arr(Uint8Array), stunned = arr(Uint8Array);
  for (const h of G.hits) { dealt[h.a][h.r] += h.amt; taken[h.v][h.r] += h.amt; }
  for (const s of G.stuns) stunned[s.v][s.r] = 1;
  for (const c of G.d.cdmg) if (c[2] >= 0 && c[1] < NR) campHit[c[2]][c[1]] = 1;
  const evB = Array.from({ length: nb }, () => []);
  for (const e of G.d.ev) if (e.who !== undefined && e.who >= 0 && e.who < nb) evB[e.who].push(e);
  for (const e of G.d.ev) {
    if (e.k === 'CaptureGems') capR[e.who][e.r] = 1;
    if (e.k === 'Submit gems' && e.who !== undefined) subR[e.who][e.r] = 1;
    if (e.k === 'Death') { dead[e.who][e.r] = 1; if (typeof e.by === 'number' && e.by >= 0 && e.by < nb && team[e.by] !== team[e.who]) kills[e.by][e.r]++; }
  }
  const deathAt = G.deaths.map((e) => ({ r: e.r, t: team[e.who], x: e.at[0], y: e.at[1], who: e.who }));
  const P = (r, b) => [G.x(r, b), G.y(r, b)];
  const offSpawn = (r, b) => G.alive(r, b) && !G.onSpawn(r, b);
  // recall arrival: a jump of 4+ tiles (dashes <= 2, crystals 3), or 3 tiles landing within 4 of the own spawn centre; an arriving
  // body may step off the spawn region in the same turn
  const teleported = (b, rr) => {
    if (rr < 1 || !G.alive(rr, b) || !G.alive(rr - 1, b)) return false;
    const j = cheb(G.x(rr - 1, b), G.y(rr - 1, b), G.x(rr, b), G.y(rr, b));
    return j > 3 || (j > 2 && G.dSpawnC(team[b], G.x(rr, b), G.y(rr, b)) <= 4);
  };
  const campDmg = G.d.dmg.filter((x) => x[2] < 0).map(([q, r, a, v]) => ({ q, r, v }));
  // ---- recall attempts: classify each Recall event
  const recInfo = [];
  const committedRec = arr(Uint8Array); // committed recall (not self-cancelled before arrival / interruption) started in round r
  for (let b = 0; b < nb; b++) {
    const evs = evB[b];
    for (let i = 0; i < evs.length; i++) {
      const e = evs[i]; if (e.k !== 'Recall') continue;
      const r0 = e.r;
      let arrive = -1;
      for (let rr = r0 + 1; rr <= Math.min(G.last, r0 + 6); rr++) if (teleported(b, rr)) { arrive = rr; break; }
      // first enemy hit / stun after the Recall step
      // a genuine recall shows no own event until it lands; if the body acted (cancel, move, re-recall...) before the arrival
      // round, that arrival belongs to a later channel (recall spam)
      if (arrive > 0 && evs[i + 1] && evs[i + 1].r < arrive) arrive = -1;
      const rLim = arrive > 0 ? arrive - 1 : r0 + 6; // an arrival means nothing interrupted the channel before it
      let hitQ = 1e15, hitR = -1;
      for (const h of G.hits) if (h.v === b && h.q > e.q && h.r <= rLim) { hitQ = h.q; hitR = h.r; break; }
      for (const s of G.stuns) if (s.v === b && s.q > e.q && s.r <= rLim && s.q < hitQ) { hitQ = s.q; hitR = s.r; break; }
      let campQ = 1e15;
      for (const c of campDmg) if (c.v === b && c.q > e.q && c.r <= rLim) { campQ = c.q; break; }
      const nxt = evs[i + 1];
      const cancelQ = nxt && nxt.k === 'Cancel channel' && nxt.r <= rLim ? nxt.q : 1e15;
      const deathE = G.deaths.find((d) => d.who === b && d.q > e.q && d.r <= r0 + 6);
      let out = 'other';
      if (arrive > 0) out = 'done';
      else if (hitQ < cancelQ && hitQ < campQ && hitQ < 1e15) out = deathE ? 'killed' : 'interrupted';
      else if (campQ < cancelQ && campQ < 1e15) out = deathE ? 'killed' : 'camp';
      else if (cancelQ < 1e15) out = 'cancel';
      else if (deathE) out = 'killed';
      const idleNext = !evs.some((f) => f.r === r0 + 1 && ['Cancel channel', 'Move', 'Attack', 'Cast ability', 'Recall', 'Submit gems'].includes(f.k));
      if (out !== 'cancel') committedRec[b][r0] = 1;
      if (G.onSpawn(Math.max(0, r0 - 1), b) || !G.alive(Math.max(0, r0 - 1), b)) continue;
      const rp = r0 - 1;
      let d0 = 99;
      for (const o of (team[b] === S ? G.ob : G.sb)) if (offSpawn(rp, o)) d0 = Math.min(d0, G.dist(rp, b, o));
      recInfo.push([team[b] === S ? 1 : 0, r0, +(G.hp(rp, b) / G.mhp(rp, b)).toFixed(3), d0, out, hitR >= 0 ? 1 : 0, idleNext ? 1 : 0, deathE ? 1 : 0]);
    }
  }
  // ---- helpers for windows
  const anyIn = (A, b, r0, r1) => { for (let r = r0; r <= r1; r++) if (A[b][r]) return true; return false; };
  const sumIn = (A, b, r0, r1) => { let s = 0; for (let r = r0; r <= r1; r++) s += A[b][r]; return s; };
  const local = (r, b) => {
    let ma = 0, me = 0, ca = 0, ce = 0, weak = 9;
    for (let o = 0; o < nb; o++) {
      if (!G.alive(r, o)) continue;
      const dd = G.dist(r, b, o);
      if (dd > 8) continue;
      if (team[o] === team[b]) { ma += G.mhp(r, o); ca += G.hp(r, o); }
      else if (!G.onSpawn(r, o)) { me += G.mhp(r, o); ce += G.hp(r, o); if (dd <= 6) weak = Math.min(weak, G.hp(r, o) / G.mhp(r, o)); }
    }
    return [me ? ma / me : 99, ce ? ca / ce : 99, weak];
  };
  const action = (b, r, eStar, d0, w) => {
    const r1 = Math.min(G.last, r + w);
    if (sumIn(dealt, b, r + 1, r1) > 0) return 'fight';
    if (anyIn(committedRec, b, r + 1, r1)) return 'recall';
    for (let rr = r + 1; rr <= r1; rr++) if (teleported(b, rr)) return 'recall';
    if (anyIn(subR, b, r + 1, r1)) return 'bank';
    if (anyIn(dead, b, r + 1, r1)) return 'dead';
    if (anyIn(campHit, b, r + 1, r1) || anyIn(capR, b, r + 1, r1)) return 'farm';
    const rb = G.alive(r1, b) ? r1 : r;
    const re = G.alive(r1, eStar) ? r1 : r;
    const d1 = cheb(G.x(rb, b), G.y(rb, b), G.x(re, eStar), G.y(re, eStar));
    const h0 = G.dSpawnC(team[b], G.x(r, b), G.y(r, b)), h1 = G.dSpawnC(team[b], G.x(rb, b), G.y(rb, b));
    if (d1 >= d0 + 2 || h1 <= h0 - 2) return 'leave';
    if (d1 <= d0 - 2) return 'toward';
    return 'hold';
  };
  const localNet = (r, b, w, rad) => {
    const [x, y] = P(r, b); let n = 0;
    for (const d of deathAt) if (d.r > r && d.r <= r + w && cheb(d.x, d.y, x, y) <= rad) n += d.t === team[b] ? -1 : 1;
    return n;
  };
  const diedIn = (b, r0, r1) => anyIn(dead, b, r0, r1);
  // ---- decision samples
  const dec = [];
  for (let r = 3; r <= G.last - 3; r += 3) {
    for (let b = 0; b < nb; b++) {
      if (!offSpawn(r, b)) continue;
      let d0 = 99, eStar = -1;
      for (let o = 0; o < nb; o++) if (team[o] !== team[b] && offSpawn(r, o)) { const dd = G.dist(r, b, o); if (dd < d0) { d0 = dd; eStar = o; } }
      if (d0 > 4) continue;
      const [mr, cr, weak] = local(r, b);
      const act = action(b, r, eStar, d0, 3);
      const recAct = anyIn(committedRec, b, r - 4, r) ? 1 : 0;
      dec.push([team[b] === S ? 1 : 0, r, +(G.hp(r, b) / G.mhp(r, b)).toFixed(3), G.mhp(r, b), d0, +mr.toFixed(3), +cr.toFixed(3), +weak.toFixed(3), act,
        diedIn(b, r + 1, r + 10) ? 1 : 0, sumIn(kills, b, r + 1, r + 10), localNet(r, b, 10, 10), recAct]);
    }
  }
  // ---- low-health crossings
  const low = [];
  for (let r = 2; r <= G.last - 1; r++) {
    for (let b = 0; b < nb; b++) {
      if (!offSpawn(r, b) || !G.alive(r - 1, b)) continue;
      const f1 = G.hp(r, b) / G.mhp(r, b), f0 = G.hp(r - 1, b) / G.mhp(r - 1, b);
      if (!(f1 < 0.35 && f0 >= 0.35)) continue;
      let d0 = 99, eStar = -1;
      for (let o = 0; o < nb; o++) if (team[o] !== team[b] && offSpawn(r, o)) { const dd = G.dist(r, b, o); if (dd < d0) { d0 = dd; eStar = o; } }
      const [mr, cr] = local(r, b);
      const act = eStar >= 0 ? action(b, r, eStar, d0, 5) : 'none';
      low.push([team[b] === S ? 1 : 0, r, d0, act, diedIn(b, r + 1, r + 15) ? 1 : 0, +mr.toFixed(3), +cr.toFixed(3), +f1.toFixed(3)]);
    }
  }
  // ---- chases
  const chase = [];
  const hitPair = new Set(); // "a,v,r" for hits either direction
  for (const h of G.hits) { hitPair.add(h.a + ',' + h.v + ',' + h.r); hitPair.add(h.v + ',' + h.a + ',' + h.r); }
  const hitAV = (a, v, r0, r1) => { for (let r = r0; r <= r1; r++) if (hitPair.has(a + ',' + v + ',' + r)) return true; return false; };
  const hitOnly = (a, v, r) => G.hitsBy[r] && G.hitsBy[r].some((h) => h.a === a && h.v === v);
  const active = new Map();
  for (let r = 2; r <= G.last; r++) {
    for (let A = 0; A < nb; A++) for (let V = 0; V < nb; V++) {
      if (team[A] === team[V] || A === V) continue;
      const key = A * 64 + V;
      if (active.has(key)) continue;
      if (!G.alive(r - 1, A) || !G.alive(r, A) || !G.alive(r - 1, V) || !G.alive(r, V)) continue;
      if (G.onSpawn(r, V)) continue;
      if (!hitAV(A, V, r - 3, r)) continue;
      const dPrev = cheb(G.x(r - 1, A), G.y(r - 1, A), G.x(r - 1, V), G.y(r - 1, V));
      const dVmove = cheb(G.x(r - 1, A), G.y(r - 1, A), G.x(r, V), G.y(r, V));
      const dAmove = cheb(G.x(r, A), G.y(r, A), G.x(r, V), G.y(r, V));
      if (!(dVmove > dPrev && dAmove < dVmove)) continue;
      if (dAmove > 10) continue;
      // run the chase
      let last = r, miss = 0, kill = 0, adied = 0, rr = r + 1;
      for (; rr <= G.last; rr++) {
        if (!G.alive(rr, V)) { if (G.deaths.some((d) => d.who === V && d.r === rr && typeof d.by === 'number' && team[d.by] === team[A])) kill = 1; else kill = 2; last = rr; break; }
        if (!G.alive(rr, A)) { adied = 1; last = rr; break; }
        if (G.onSpawn(rr, V)) { last = rr; break; }
        const dd = cheb(G.x(rr, A), G.y(rr, A), G.x(rr, V), G.y(rr, V));
        if (dd > 10) break;
        const closes = dd < cheb(G.x(rr - 1, A), G.y(rr - 1, A), G.x(rr, V), G.y(rr, V));
        if (closes || hitOnly(A, V, rr)) { last = rr; miss = 0; } else if (++miss >= 2) break;
      }
      const end = last;
      active.set(key, end);
      let ad10 = 0; for (let k = end + 1; k <= Math.min(G.last, end + 10); k++) if (dead[A][k]) { ad10 = 1; break; }
      chase.push([team[A] === S ? 1 : 0, type[A], +(G.hp(r - 1, V) / G.mhp(r - 1, V)).toFixed(3), end - r + 1, kill === 1 ? 1 : 0, adied, ad10, r]);
    }
    for (const [k, e] of active) if (e < r) active.delete(k);
  }
  console.log(JSON.stringify({ key: row.key, match: row.match, map: row.map, swon: row.swon, final: G.final, dec, low, rec: recInfo, chase }));
}
