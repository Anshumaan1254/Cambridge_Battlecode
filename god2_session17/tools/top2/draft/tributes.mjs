#!/usr/bin/env node
// Tribute attempts per champion type from fight dumps: each 'Submit gems' start (bag from the round state) and whether a 'Banked'
// by the same body follows within ceil(bag/10)+3 rounds; failed attempts are attributed to death / stun / enemy altar lock / other.
// One JSON line per tribute start: { key, file, win, mine (study team's body), type, r, bag, ok, cause, banked }.
//   node tools/top2/draft/tributes.mjs KEY...
import fs from 'node:fs';
import zlib from 'node:zlib';

const PRE = { pbg: '38e6d8c4', ifish: '1890540d', pantheon: '547efb5b', coo: '1570a113', cm: 'ad5474c2', nyx: '6f7fd199' };
for (const key of process.argv.slice(2)) {
  const idx = new Map();
  for (const line of fs.readFileSync(`C:/battlecode/cache/t2/${key}/index.jsonl`, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const m = JSON.parse(line);
    idx.set(m.matchId.slice(0, 8), m);
  }
  const dir = `C:/battlecode/cache/t2dump/${key}/`;
  const seen = new Set();
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json.gz')).sort()) {
    const row = idx.get(f.match(/_([0-9a-f]{8})\.json\.gz$/)[1]);
    if (!row) continue;
    const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(dir + f)));
    const sig = `${row.map}|${d.meta.finalRound}|${d.meta.submitted.join(',')}|${d.meta.outcome}`;
    if (seen.has(sig)) continue;
    seen.add(sig);
    const me = row.teams.find((t) => t.teamId.startsWith(PRE[key]));
    const st = me.side === 'a' ? 0 : 1;
    const win = (d.meta.outcome === 1 && st === 0) || (d.meta.outcome === 2 && st === 1) ? 1 : 0;
    const bag = new Map(); // `${r}:${body}` -> gems at end of round r
    for (const [r, s0, s1, sts] of d.R) for (const s of sts) bag.set(`${r}:${s[0]}`, s[6]);
    const banks = d.ev.filter((e) => e.k === 'Banked');
    const deaths = d.ev.filter((e) => e.k === 'Death');
    const locks = d.ev.filter((e) => e.k === 'Place altar lock');
    const starts = d.ev.filter((e) => e.k === 'Submit gems');
    let lastStart = new Map();
    for (const e of starts) {
      const b = d.meta.bodies[e.who];
      if (!b) continue;
      // skip repeated start attempts of the same channel (one per body until it resolves)
      const prev = lastStart.get(e.who);
      if (prev !== undefined && e.r <= prev) continue;
      const g = bag.get(`${e.r - 1}:${e.who}`) ?? bag.get(`${e.r}:${e.who}`) ?? 0;
      const dur = Math.max(1, Math.ceil(g / 10));
      const end = e.r + dur + 3;
      lastStart.set(e.who, end);
      const bk = banks.find((x) => x.who === e.who && x.r >= e.r && x.r <= end);
      let cause = bk ? 'ok' : 'other';
      if (!bk) {
        if (deaths.find((x) => x.who === e.who && x.r >= e.r && x.r <= end)) cause = 'death';
        else if (d.stun.find(([q, r, a, v]) => v === e.who && r >= e.r && r <= end)) cause = 'stun';
        else if (locks.find((x) => d.meta.bodies[x.who] && d.meta.bodies[x.who].team !== b.team && x.r >= e.r - 1 && x.r <= end)) cause = 'lock';
      }
      console.log(JSON.stringify({ key, file: f, map: row.map, win, mine: b.team === st ? 1 : 0, type: b.type, r: e.r, bag: g, ok: bk ? 1 : 0, cause,
        banked: bk ? bk.gems : 0 }));
    }
  }
}
