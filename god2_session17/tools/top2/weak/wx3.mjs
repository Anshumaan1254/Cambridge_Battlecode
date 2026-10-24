#!/usr/bin/env node
// More weakness features (an_weak) per study-team fightdump dump, for the study team S and its opponent O:
//  campDeaths  every death by a camp: camp type of the killing blow, enemy champions within 8, champion damage taken in the 10 rounds before
//  ciKills     Cassi & Issac deaths: which body took the killing blow (the other one dies with it)
//  hpState     deaths per alive body-round by the team's max-health share (team maxHp sum / both teams), buckets <0.43 / 0.43-0.57 / >0.57
//  recalls     recall starts with an enemy champion within 6: hp share, outcome within 8 rounds (home = completed, dead, interrupted)
//  heavy       per team: hits on golem / monolith camps (rounds), deaths within 8 tiles of a golem / monolith while hitting it in the last 10 r,
//              and enemy champions within 8 at those deaths (third party)
//   node tools/top2/weak/wx3.mjs dump.json.gz...
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
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
  const campBy = new Map(d.meta.camps.map((c) => [c.index, { ...c, type: c.type === 5 ? 'golem' : c.type }]));
  const out = { file: base, key, S, win: me.result === 'win' ? 1 : 0, T: {} };
  for (const t of [S, 1 - S]) out.T[t === S ? 'S' : 'O'] = { campDeaths: [], ciKills: { Cassi: 0, Issac: 0 }, hp: { lo: [0, 0], ev: [0, 0], hi: [0, 0] }, recalls: [], heavyHitRounds: 0, heavyDeaths: 0, heavyDeaths3p: 0 };
  const X = (t) => out.T[t === S ? 'S' : 'O'];
  // death list with killing step
  const deaths = d.ev.filter((e) => e.k === 'Death');
  const dmgByQ = new Map(); for (const x of d.dmg) { if (!dmgByQ.has(x[0])) dmgByQ.set(x[0], []); dmgByQ.get(x[0]).push(x); }
  const camHits = new Map(); // body -> Map(round -> campType) for golem/mono hits
  for (const x of d.cdmg) { const c = campBy.get(x[3]); if (!c || (c.type !== 'golem' && c.type !== 'monolith')) continue; if (!camHits.has(x[2])) camHits.set(x[2], new Map()); camHits.get(x[2]).set(x[1], c.type); }
  for (const [b, m] of camHits) X(teamOf(b)).heavyHitRounds += m.size;
  const enemyNear = (r, b, t, R) => { const m = PM.get(r); if (!m) return 0; const p = m.get(b); if (!p) return 0; let n = 0; for (const c of m.values()) if (c[5] && teamOf(c[0]) !== t && cheb(c[1], c[2], p[1], p[2]) <= R) n++; return n; };
  for (const e of deaths) {
    const t = teamOf(e.who);
    if (e.by === 'camp') {
      const blows = (dmgByQ.get(e.q) || []).filter((x) => x[3] === e.who && x[2] < 0);
      const camp = blows.length ? campBy.get(-1 - blows[0][2]) : null;
      let champDmg10 = 0; for (const x of d.dmg) if (x[3] === e.who && x[2] >= 0 && x[1] >= e.r - 10 && x[1] <= e.r) champDmg10 += x[4];
      const hitT = new Set(); for (const x of d.cdmg) if (x[2] === e.who && x[1] >= e.r - 10 && x[1] <= e.r) { const c = campBy.get(x[3]); if (c) hitT.add(c.type); }
      X(t).campDeaths.push({ r: e.r, ty: tyOf(e.who), camp: camp ? camp.type : '?', en8: enemyNear(e.r - 1, e.who, t, 8), champDmg10, bag: e.bag, hit10: [...hitT].join('+') || 'none' });
    }
    if (tyOf(e.who) === 'Cassi' || tyOf(e.who) === 'Issac') {
      // the body that took a damaging hit in the death step is the one that was killed; the partner dies by the link
      const hit = (dmgByQ.get(e.q) || []).some((x) => x[3] === e.who);
      if (hit) X(t).ciKills[tyOf(e.who)]++;
    }
    // heavy camp death: the victim hit a golem/monolith in the last 10 rounds
    const hm = camHits.get(e.who);
    if (hm) { let hh = false; for (let k = e.r - 10; k <= e.r; k++) if (hm.has(k)) hh = true; if (hh) { X(t).heavyDeaths++; if (enemyNear(e.r - 1, e.who, t, 8) > 0) X(t).heavyDeaths3p++; } }
  }
  // hp state: per round, team max-hp share; per alive body-round and deaths
  const deathR = new Map(); for (const e of deaths) { const k = e.r; if (!deathR.has(k)) deathR.set(k, []); deathR.get(k).push(teamOf(e.who)); }
  for (let r = 20; r <= final; r++) {
    const m = PM.get(r - 1); if (!m) continue;
    const mh = [0, 0], alive = [0, 0]; for (const c of m.values()) { const t = teamOf(c[0]); mh[t] += c[4]; if (c[5]) alive[t]++; }
    for (const t of [0, 1]) {
      const sh = mh[t] / (mh[0] + mh[1]); const k = sh < 0.43 ? 'lo' : sh > 0.57 ? 'hi' : 'ev';
      X(t).hp[k][0] += alive[t];
      for (const tt of deathR.get(r) || []) if (tt === t) X(t).hp[k][1]++;
    }
  }
  // recalls near enemies (skip recall-spam: only count a start if the body did not issue a Recall in the previous round)
  const recBy = new Map(); for (const e of d.ev) if (e.k === 'Recall') { if (!recBy.has(e.who)) recBy.set(e.who, new Set()); recBy.get(e.who).add(e.r); }
  for (const [b, rs] of recBy) {
    const t = teamOf(b);
    for (const r of rs) {
      if (rs.has(r - 1)) continue;
      const p = PM.get(r - 1)?.get(b); if (!p || !p[5]) continue;
      const en = enemyNear(r - 1, b, t, 6); if (!en) continue;
      // outcome
      let res = 'interrupted';
      for (let k = r; k <= r + 8; k++) { const c = PM.get(k)?.get(b); if (!c) continue; if (!c[5]) { res = 'dead'; break; } const sp = PM.get(1)?.get(b); if (sp && cheb(c[1], c[2], sp[1], sp[2]) <= 2 && cheb(p[1], p[2], sp[1], sp[2]) > 3) { res = 'home'; break; } }
      X(t).recalls.push({ r, ty: tyOf(b), hp: +(p[3] / p[4]).toFixed(2), en, res, spam: rs.size > 300 ? 1 : 0 });
    }
  }
  console.log(JSON.stringify(out));
}
