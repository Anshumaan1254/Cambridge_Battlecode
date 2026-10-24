#!/usr/bin/env node
// Per-body role metrics from fight dumps (tools/live/fightdump.mjs format) for the draft / composition study: which champion of a
// team banks, captures, carries gold, deals / takes champion damage, kills, dies (and with how many gems), stuns, heals.
// One JSON line per dump: { file, mid8, map, key, side, studyTeam (0/1), win (study team won), finalRound, submitted, sig,
//   bodies: [{ i, team, type, banked, nBank, capG, capGold, nCap, kills, deaths, bagLost, dDone, dTaken, campDmg, stunDone,
//   stunTaken, healDone, alive, meanBag, maxBag, maxHp, gold, recalls, locks, wards, firstBank }] }
//   node tools/top2/draft/roles.mjs KEY...        (reads C:/battlecode/cache/t2dump/<KEY>/*.json.gz + t2/<KEY>/index.jsonl)
import fs from 'node:fs';
import zlib from 'node:zlib';

const keys = process.argv.slice(2);
for (const key of keys) {
  const idx = new Map();
  for (const line of fs.readFileSync(`C:/battlecode/cache/t2/${key}/index.jsonl`, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const m = JSON.parse(line);
    idx.set(m.matchId.slice(0, 8), m);
  }
  const dir = `C:/battlecode/cache/t2dump/${key}/`;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json.gz')).sort()) {
    const mid8 = f.match(/_([0-9a-f]{8})\.json\.gz$/)[1];
    const row = idx.get(mid8);
    if (!row) { process.stderr.write(`no index row for ${f}\n`); continue; }
    let d;
    try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(dir + f))); } catch (e) { process.stderr.write(`bad ${f}\n`); continue; }
    const PRE = { pbg: '38e6d8c4', ifish: '1890540d', pantheon: '547efb5b', coo: '1570a113', cm: 'ad5474c2', nyx: '6f7fd199' }[key];
    const me = row.teams.find((t) => t.teamId.startsWith(PRE));
    const studyTeam = me.side === 'a' ? 0 : 1;
    const B = d.meta.bodies.map((b) => ({ i: b.index, team: b.team, type: b.type, banked: 0, nBank: 0, capG: 0, capGold: 0, nCap: 0, kills: 0,
      deaths: 0, bagLost: 0, dDone: 0, dTaken: 0, campDmg: 0, stunDone: 0, stunTaken: 0, healDone: 0, alive: 0, bagSum: 0, maxBag: 0, maxHp: 0,
      gold: 0, recalls: 0, locks: 0, wards: 0, firstBank: -1, deathBags: [] }));
    for (const e of d.ev) {
      const b = B[e.who];
      if (e.k === 'Banked' && b) { b.banked += e.gems; b.nBank++; if (b.firstBank < 0) b.firstBank = e.r; }
      else if (e.k === 'CaptureGems' && b) { b.capG += e.gems; b.capGold += e.gold; b.nCap++; }
      else if (e.k === 'Death' && b) {
        b.deaths++; b.bagLost += e.bag || 0; b.deathBags.push([e.r, e.bag || 0, e.by]);
        if (typeof e.by === 'number' && B[e.by]) B[e.by].kills++;
      }
      else if (e.k === 'Recall' && b) b.recalls++;
      else if (e.k === 'Place altar lock' && b) b.locks++;
      else if (e.k === 'Place ward' && b) b.wards++;
    }
    for (const [q, r, a, v, amt] of d.dmg) {
      if (a >= 0 && B[a] && B[v] && B[a].team !== B[v].team) { B[a].dDone += amt; B[v].dTaken += amt; }
    }
    for (const [q, r, a, c, amt] of d.cdmg) if (B[a]) B[a].campDmg += amt;
    for (const [q, r, a, v] of d.stun) { if (a >= 0 && B[a]) B[a].stunDone++; if (B[v]) B[v].stunTaken++; }
    for (const [q, r, c, t, amt] of d.heal) if (B[c]) B[c].healDone += amt;
    for (const [r, s0, s1, st] of d.R) {
      for (const [bi, x, y, hp, maxHp, alive, gems, gold] of st) {
        const b = B[bi];
        if (!b) continue;
        if (alive) { b.alive++; b.bagSum += gems; if (gems > b.maxBag) b.maxBag = gems; }
        b.maxHp = maxHp; b.gold = gold;
      }
    }
    for (const b of B) { b.meanBag = b.alive ? +(b.bagSum / b.alive).toFixed(1) : 0; delete b.bagSum; }
    const win = (d.meta.outcome === 1 && studyTeam === 0) || (d.meta.outcome === 2 && studyTeam === 1) ? 1 : 0;
    const sig = `${row.map}|${d.meta.finalRound}|${d.meta.submitted.join(',')}|${d.meta.outcome}`;
    console.log(JSON.stringify({ file: f, mid8, map: row.map, key, side: me.side, studyTeam, win, result: me.result, finalRound: d.meta.finalRound,
      submitted: d.meta.submitted, sig, created: row.createdAt, opp: row.teams.find((t) => t !== me).name, bodies: B }));
  }
}
