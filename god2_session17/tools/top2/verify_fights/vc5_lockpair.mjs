#!/usr/bin/env node
// Verify C5 guard-lock inference: for every altar lock L1 (team A, altar X), the next lock L2 placed by the other team on X within
// 10 rounds: rounds between, basic attacks on X by the other team in between (5 clear a lock), and whether team A started a
// tribute at X between L1 and L2. If L2 lands with < 5 attacks in between, L1 did not block it (or was consumed).
//   node vc5_lockpair.mjs games.json mapgeo.jsonl SHARD NSHARD > out.jsonl
import { loadGeo, loadGame, readGames } from './vlib.mjs';
const [gf, geof, shard, nsh] = process.argv.slice(2);
const geo = loadGeo(geof);
const games = readGames(gf).filter((_, i) => i % +nsh === +shard);
for (const row of games) {
  const G = loadGame(row, geo);
  const ev = G.d.ev, team = G.team;
  const ak = (p) => p ? p[0] + ',' + p[1] : '';
  const locks = ev.filter((e) => e.k === 'Place altar lock' && e.who !== undefined);
  const out = [];
  for (const l1 of locks) {
    const A = team[l1.who], X = ak(l1.to);
    const l2 = locks.find((l) => l.q > l1.q && ak(l.to) === X && l.r - l1.r <= 10);
    if (!l2 || team[l2.who] === A) continue; // the next lock on X within 10 rounds must be the other team's
    let atk = 0, ownTrib = 0, ownSameLock = 0;
    for (const e of ev) {
      if (e.q <= l1.q || e.q >= l2.q) continue;
      if (e.k === 'Attack' && ak(e.to) === X && team[e.who] !== A) atk++;
      if (e.k === 'Submit gems' && ak(e.to) === X && team[e.who] === A) ownTrib++;
    }
    out.push([A === G.S ? 1 : 0, l1.r, l2.r, X, atk, ownTrib]);
  }
  console.log(JSON.stringify({ key: row.key, match: row.match, map: row.map, dump: row.dump, n: locks.length, pairs: out }));
}
