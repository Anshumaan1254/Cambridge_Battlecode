#!/usr/bin/env node
// Verify C5 window sensitivity: for every tribute attempt, the opposing team's responses (hits / stuns on the channeller, locks
// on that altar) counted (a) during the actual channel (start .. the step that ended it) and (b) during the nominal channel length
// (start round .. start + ceil(bag/10)), with the closest opposing body in each window. One JSON line per game.
//   node vc5_win.mjs games.json mapgeo.jsonl SHARD NSHARD > out.jsonl
import { loadGeo, loadGame, readGames, cheb } from './vlib.mjs';
const [gf, geof, shard, nsh] = process.argv.slice(2);
const geo = loadGeo(geof);
const games = readGames(gf).filter((_, i) => i % +nsh === +shard);
for (const row of games) {
  const G = loadGame(row, geo);
  const { nb, team, type } = G;
  const ev = G.d.ev;
  const ak = (p) => p[0] + ',' + p[1];
  const subs = ev.filter((e) => e.k === 'Submit gems' && e.who !== undefined);
  const ends = ev.filter((e) => e.who !== undefined && ['Gems submitted', 'Cancel channel', 'Death', 'Move', 'Attack', 'Cast ability', 'Recall', 'Submit gems'].includes(e.k));
  const locks = ev.filter((e) => e.k === 'Place altar lock' && e.who !== undefined);
  const out = [];
  for (const s of subs) {
    const b = s.who, t = team[b], bag = G.gems(s.r, b), dur = Math.max(1, Math.ceil(bag / 10));
    // actual end: first ending event of this body after the start, or an opposing stun on it, or an opposing lock at that altar
    let q1 = 1e15, out1 = 'open';
    for (const e of ends) { if (e.who !== b || e.q <= s.q) continue; q1 = e.q; out1 = e.k; break; }
    for (const x of G.stuns) if (x.v === b && x.q > s.q && x.q < q1) { q1 = x.q; out1 = 'stun'; break; }
    for (const l of locks) if (team[l.who] !== t && ak(l.to) === ak(s.to) && l.q > s.q && l.q < q1) { q1 = l.q; out1 = 'lock'; break; }
    const rEndNom = s.r + dur;
    const win = (lo, hiQ, hiR) => {
      let hits = 0, stuns = 0, lk = 0, minD = 99;
      for (const h of G.hits) if (h.v === b && h.q > lo && h.q <= hiQ && h.r <= hiR) hits++;
      for (const x of G.stuns) if (x.v === b && x.q > lo && x.q <= hiQ && x.r <= hiR) stuns++;
      for (const l of locks) if (team[l.who] !== t && ak(l.to) === ak(s.to) && l.q > lo && l.q <= hiQ && l.r <= hiR) lk++;
      for (let r = s.r; r <= Math.min(hiR, G.last); r++) {
        const bx = G.alive(r, b) ? G.x(r, b) : G.x(Math.max(0, r - 1), b), by = G.alive(r, b) ? G.y(r, b) : G.y(Math.max(0, r - 1), b);
        for (let o = 0; o < nb; o++) if (team[o] !== t && G.alive(r, o)) minD = Math.min(minD, cheb(G.x(r, o), G.y(r, o), bx, by));
      }
      return [hits, stuns, lk, minD];
    };
    const qr1 = q1 < 1e15 ? (G.d.ev.find((e) => e.q === q1)?.r ?? rEndNom) : G.final;
    const A = win(s.q, q1, 1e9);
    const N = win(s.q, 1e15, rEndNom);
    out.push([t === G.S ? 1 : 0, type[b], s.r, bag, dur, out1, qr1, ...A, ...N]);
  }
  console.log(JSON.stringify({ key: row.key, match: row.match, map: row.map, t: out }));
}
