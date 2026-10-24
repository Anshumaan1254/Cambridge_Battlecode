#!/usr/bin/env node
// Verify C2 / C5 / C6 (an_fights.md), independent implementation over fightdump dumps. One JSON line per game with:
//  trib[]: every tribute attempt ('Submit gems'), both teams: who, team(1 = S), type, r, bag, altar, score before (own, enemy),
//          outcome (done / killed / stunned / locked / cancel / open / other) and end round, opposing responses during the channel
//          (hits, damage, stuns, opposing lock at that altar), closest opposing body during the channel and at the start, nearest
//          enemy at the start, allies within 6 at the start, own lock placed on that altar in the 3 rounds before.
//  locks[]: every 'Place altar lock': team, r, altar, guard (own tribute starts at that altar within 3 rounds after),
//          counter (an enemy tribute channel at that altar was running when placed).
//  caps[]: every CaptureGems: team, who, type, r, gained, bag after, walking distance to a tribute tile, enemy within 8, next event
//          of that body (bank = 'Gems submitted' / cap / death / end) and its round, whether a recall completed in between.
//  deaths[]: team, type, r, bag, by-champion.
//  prism[]: every 3rd round, each alive Prism off its spawn with an enemy (alive, off its spawn) within 6: team, r, bag, hp frac,
//          max hp, damage dealt to champions in r+1..r+5, died in r+1..r+10, local max-health ratio within 8.
//   node vc_econ.mjs games.json mapgeo.jsonl SHARD NSHARD > out.jsonl
import { loadGeo, loadGame, readGames, cheb } from './vlib.mjs';
const [gf, geof, shard, nsh] = process.argv.slice(2);
const geo = loadGeo(geof);
const games = readGames(gf).filter((_, i) => i % +nsh === +shard);
for (const row of games) {
  const G = loadGame(row, geo);
  const { nb, team, type } = G;
  const S = G.S;
  const ev = G.d.ev; // already in q order
  const altarKey = (p) => p[0] + ',' + p[1];
  // ---------- tributes
  const trib = [];
  const openT = new Map(); // body -> tribute record
  const locksAll = [];
  const finish = (t, out, r, q) => { t.out = out; t.r1 = r; t.q1 = q; openT.delete(t.who); };
  // index stuns and hits by q to merge with events in step order
  const stream = [];
  for (const e of ev) stream.push({ q: e.q, e });
  for (const s of G.stuns) stream.push({ q: s.q, s });
  for (const h of G.hits) stream.push({ q: h.q, h });
  stream.sort((a, b) => a.q - b.q);
  for (const it of stream) {
    if (it.h) { const h = it.h; const t = openT.get(h.v); if (t && team[h.a] !== team[h.v]) { t.hits++; t.dmg += h.amt; if (t.firstHitR < 0) t.firstHitR = h.r; } continue; }
    if (it.s) { const s = it.s; const t = openT.get(s.v); if (t) { t.stuns++; finish(t, 'stunned', s.r, s.q); } continue; }
    const e = it.e;
    if (e.k === 'Submit gems' && e.who !== undefined) {
      const prev = openT.get(e.who); if (prev) finish(prev, 'restart', e.r, e.q);
      const r = e.r, b = e.who, pr = Math.max(0, r - 1);
      let near = 99, al6 = 0;
      for (let o = 0; o < nb; o++) {
        if (o === b || !G.alive(pr, o)) continue;
        const dd = cheb(G.x(pr, o), G.y(pr, o), G.x(r, b), G.y(r, b));
        if (team[o] !== team[b]) { if (!G.onSpawn(pr, o)) near = Math.min(near, dd); } else if (dd <= 6) al6++;
      }
      const t = { who: b, s: team[b] === S ? 1 : 0, ty: type[b], r, q: e.q, bag: G.gems(r, b), alt: altarKey(e.to), own: G.SUB[team[b]][pr], opp: G.SUB[1 - team[b]][pr],
        out: 'open', r1: G.final, q1: 1e12, hits: 0, dmg: 0, stuns: 0, lockOpp: 0, firstHitR: -1, near0: near, al6,
        guard: locksAll.some((l) => l.team === team[b] && l.alt === altarKey(e.to) && r - l.r <= 3 && r >= l.r) ? 1 : 0 };
      trib.push(t); openT.set(b, t);
    } else if (e.k === 'Gems submitted' && e.who !== undefined) {
      const t = openT.get(e.who); if (t) finish(t, 'done', e.r, e.q);
    } else if (e.k === 'Cancel channel' && e.who !== undefined) {
      const t = openT.get(e.who); if (t) finish(t, 'cancel', e.r, e.q);
    } else if (e.k === 'Death') {
      const t = openT.get(e.who); if (t) finish(t, 'killed', e.r, e.q);
    } else if (e.k === 'Place altar lock' && e.who !== undefined) {
      const lt = team[e.who], ak = altarKey(e.to);
      let counter = 0;
      for (const t of [...openT.values()]) if (t.alt === ak && team[t.who] !== lt) { t.lockOpp++; counter = 1; finish(t, 'locked', e.r, e.q); }
      locksAll.push({ team: lt, s: lt === S ? 1 : 0, who: e.who, ty: type[e.who], r: e.r, alt: ak, counter, guard: 0 });
    } else if ((e.k === 'Move' || e.k === 'Attack' || e.k === 'Cast ability' || e.k === 'Recall') && e.who !== undefined) {
      const t = openT.get(e.who); if (t) finish(t, 'other', e.r, e.q);
    }
  }
  // guard flag for locks: own tribute at that altar within 3 rounds after
  for (const l of locksAll) l.guard = trib.some((t) => team[t.who] === l.team && t.alt === l.alt && t.r >= l.r && t.r - l.r <= 3) ? 1 : 0;
  // closest opposing body during the channel (rounds r..r1)
  for (const t of trib) {
    let mn = 99, mn4r = 0;
    for (let r = t.r; r <= Math.min(t.r1, G.last); r++) {
      let m = 99;
      for (let o = 0; o < nb; o++) { if (team[o] === team[t.who] || !G.alive(r, o)) continue; m = Math.min(m, cheb(G.x(r, o), G.y(r, o), G.x(r, t.who), G.y(r, t.who))); }
      mn = Math.min(mn, m); if (m <= 4) mn4r++;
    }
    t.minD = mn; t.r4 = mn4r; t.dur = Math.max(1, Math.ceil(t.bag / 10));
  }
  // ---------- captures and bag fate
  const caps = [];
  const byBody = Array.from({ length: nb }, () => []);
  for (const e of ev) {
    if (e.who === undefined) continue;
    if (e.k === 'CaptureGems' || e.k === 'Gems submitted' || e.k === 'Death' || e.k === 'Submit gems') byBody[e.who].push(e);
  }
  for (const e of ev) {
    if (e.k !== 'CaptureGems') continue;
    const b = e.who, r = e.r;
    let enemy8 = 0;
    for (let o = 0; o < nb; o++) if (team[o] !== team[b] && G.alive(r, o) && !G.onSpawn(r, o) && cheb(G.x(r, o), G.y(r, o), e.at[0], e.at[1]) <= 8) enemy8 = 1;
    let next = 'end', nr = G.final;
    for (const f of byBody[b]) {
      if (f.q <= e.q) continue;
      if (f.k === 'CaptureGems') { next = 'cap'; nr = f.r; break; }
      if (f.k === 'Gems submitted') { next = 'bank'; nr = f.r; break; }
      if (f.k === 'Death') { next = 'death'; nr = f.r; break; }
    }
    // via spawn: the body stood on its spawn between the capture and the next event
    let via = 0;
    for (let rr = r + 1; rr <= Math.min(nr, G.last); rr++) if (G.alive(rr, b) && G.onSpawn(rr, b)) { via = 1; break; }
    caps.push({ s: team[b] === S ? 1 : 0, who: b, ty: type[b], r, g: e.gems, bag: G.gems(r, b), da: G.dAltar(e.at[0], e.at[1]), e8: enemy8, next, nr, via });
  }
  const deaths = G.deaths.map((e) => ({ s: team[e.who] === S ? 1 : 0, ty: type[e.who], r: e.r, bag: e.bag || 0, champ: typeof e.by === 'number' && e.by >= 0 && team[e.by] !== undefined && team[e.by] !== team[e.who] ? 1 : 0 }));
  // ---------- Prism samples
  const prism = [];
  for (let b = 0; b < nb; b++) {
    if (type[b] !== 'Prism') continue;
    const dmgBy = new Float64Array(G.NR);
    for (const h of G.hits) if (h.a === b && h.r < G.NR) dmgBy[h.r] += h.amt;
    const deathR = G.deaths.filter((e) => e.who === b).map((e) => e.r);
    for (let r = 3; r <= G.last - 1; r += 3) {
      if (!G.alive(r, b) || G.onSpawn(r, b)) continue;
      let ne = 99, mA = 0, mE = 0;
      for (let o = 0; o < nb; o++) {
        if (!G.alive(r, o)) continue;
        const dd = G.dist(r, b, o);
        if (team[o] === team[b]) { if (dd <= 8) mA += G.mhp(r, o); }
        else if (!G.onSpawn(r, o)) { ne = Math.min(ne, dd); if (dd <= 8) mE += G.mhp(r, o); }
      }
      if (ne > 6) continue;
      let dm = 0; for (let rr = r + 1; rr <= Math.min(G.last, r + 5); rr++) dm += dmgBy[rr];
      const died = deathR.some((x) => x > r && x <= r + 10) ? 1 : 0;
      prism.push([team[b] === S ? 1 : 0, r, G.gems(r, b), +(G.hp(r, b) / G.mhp(r, b)).toFixed(3), G.mhp(r, b), Math.round(dm), died, +(mA / Math.max(1, mE)).toFixed(3), ne]);
    }
  }
  console.log(JSON.stringify({ key: row.key, map: row.map, match: row.match, swon: row.swon, final: G.final, sidx: S, sub: [G.SUB[S][G.last], G.SUB[1 - S][G.last]],
    sPrism: G.sb.some((b) => type[b] === 'Prism') ? 1 : 0, oPrism: G.ob.some((b) => type[b] === 'Prism') ? 1 : 0,
    trib, locks: locksAll, caps, deaths, prism }));
}
