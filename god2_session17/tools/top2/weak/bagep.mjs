#!/usr/bin/env node
// Bag episodes (an_weak) from fightdump dumps of study-team games: for every body (both teams), an episode starts when its carried gems
// reach MIN (default 100) and ends when the bag drops below MIN/2 (banked, died, or the game ended). Per episode: peak bag, rounds held,
// tribute starts and how each ended (done / self-cancel / stun / lock / death / other), for self-cancels whether an enemy champion was
// within 6 (and 8) of the carrier at the cancel and whether the carrier hit a champion within 3 rounds after it, the end (bank / death
// (bag to the killer's team) / game end), rounds from the first tribute start to the end, and enemies within 6 at the first start.
//   node tools/top2/weak/bagep.mjs dump.json.gz... [MIN=100 via env BAGMIN]   -> one JSON line per game {file, key, S, win, eps: [...]}
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
const MIN = +(process.env.BAGMIN || 100);
const IDX = new Map();
function idx(key) {
  if (IDX.has(key)) return IDX.get(key);
  const m = new Map(); const p = `C:/battlecode/cache/t2/${key}/index.jsonl`;
  if (fs.existsSync(p)) for (const l of fs.readFileSync(p, 'utf8').split('\n')) { if (!l.trim()) continue; const r = JSON.parse(l); m.set(r.matchId.slice(0, 8), r); }
  IDX.set(key, m); return m;
}
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
for (const file of process.argv.slice(2)) {
  const base = path.basename(file); const key = path.basename(path.dirname(file));
  const mm = base.match(/^(.*)_([0-9a-f]{8})\.json\.gz$/); if (!mm) continue;
  const row = idx(key).get(mm[2]); if (!row) continue;
  const me = row.teams.find((t) => t.teamId.startsWith(TEAMS[key]));
  const S = me.side === 'a' ? 0 : 1;
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const teamOf = (i) => d.meta.bodies[i]?.team, tyOf = (i) => d.meta.bodies[i]?.type;
  const PM = new Map(); for (const e of d.R) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(e[0], m); }
  const final = d.meta.finalRound;
  const evBy = new Map(); for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
  const champHitR = new Map(); for (const x of d.dmg) { if (x[2] >= 0 && teamOf(x[2]) !== teamOf(x[3])) { if (!champHitR.has(x[2])) champHitR.set(x[2], new Set()); champHitR.get(x[2]).add(x[1]); } }
  const enemiesWithin = (r, b, R) => { const m = PM.get(r); if (!m) return 0; const me2 = m.get(b); if (!me2) return 0; let n = 0; for (const c of m.values()) if (c[5] && teamOf(c[0]) !== teamOf(b) && cheb(c[1], c[2], me2[1], me2[2]) <= R) n++; return n; };
  const locks = d.ev.filter((e) => e.k === 'Place altar lock');
  const stunsOn = new Map(); for (const s of d.stun) { if (!stunsOn.has(s[3])) stunsOn.set(s[3], []); stunsOn.get(s[3]).push(s); }
  const deaths = new Map(); for (const e of d.ev) if (e.k === 'Death') { if (!deaths.has(e.who)) deaths.set(e.who, []); deaths.get(e.who).push(e); }
  const eps = [];
  for (const b of d.meta.bodies) {
    const i = b.index; let ep = null;
    for (let r = 1; r <= final; r++) {
      const c = PM.get(r)?.get(i); if (!c) continue;
      const bag = c[5] ? c[6] : 0;
      if (!ep && bag >= MIN) ep = { team: b.team, ty: b.type, b: i, r0: r, peak: bag, tribs: [], end: null, rEnd: null };
      if (ep) {
        if (bag > ep.peak) ep.peak = bag;
        if (bag < MIN / 2 || r === final) {
          ep.rEnd = r;
          const dd = (deaths.get(i) || []).find((x) => x.r <= r && x.r >= r - 1);
          ep.end = r === final && bag >= MIN / 2 ? 'gameEnd' : dd ? 'death' : 'bank';
          if (dd) { ep.killerTeam = typeof dd.by === 'number' ? teamOf(dd.by) : 'camp'; ep.killer = typeof dd.by === 'number' ? tyOf(dd.by) : 'camp'; ep.deathBag = dd.bag; }
          // tribute starts inside the episode
          for (const e of (evBy.get(i) || [])) {
            if (e.k !== 'Submit gems' || e.r < ep.r0 || e.r > r) continue;
            const list = (evBy.get(i) || []).filter((x) => x.q > e.q && x.k !== 'Banked');
            const nx = list[0];
            let res = 'open', rr = final;
            if (nx) { rr = nx.r; res = nx.k === 'Gems submitted' ? 'done' : nx.k === 'Death' ? 'death' : nx.k === 'Cancel channel' ? 'self' : nx.k === 'Submit gems' ? 'restart' : 'other'; }
            const qEnd = nx ? nx.q : 1e12;
            const lk = locks.some((L) => L.q > e.q && L.q <= qEnd && teamOf(L.who) !== b.team && cheb(L.to[0], L.to[1], e.to[0], e.to[1]) === 0);
            const st = (stunsOn.get(i) || []).some((s) => s[0] > e.q && s[0] <= qEnd);
            if (res !== 'done' && res !== 'death') { if (lk) res = 'lock'; else if (st) res = 'stun'; }
            const t = { r: e.r, bag: PM.get(e.r)?.get(i)?.[6] ?? 0, res, len: rr - e.r, en6s: enemiesWithin(e.r, i, 6) };
            if (res === 'self' || res === 'other') { t.en6 = enemiesWithin(rr, i, 6); t.en8 = enemiesWithin(rr, i, 8); let hit = false; for (let k = rr; k <= rr + 3; k++) if (champHitR.get(i)?.has(k)) hit = true; t.hitAfter = hit ? 1 : 0; }
            ep.tribs.push(t);
          }
          ep.held = ep.rEnd - ep.r0;
          const first = ep.tribs[0];
          ep.firstTrib = first ? first.r - ep.r0 : null;
          ep.tribToEnd = first ? ep.rEnd - first.r : null;
          eps.push(ep); ep = null;
        }
      }
    }
  }
  console.log(JSON.stringify({ file: base, key, map: mm[1], S, win: me.result === 'win' ? 1 : 0, final, sub: [d.meta.submitted[S], d.meta.submitted[1 - S]], eps }));
}
