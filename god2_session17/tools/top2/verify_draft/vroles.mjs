#!/usr/bin/env node
// vroles.mjs (verify_draft): independent per-game body metrics + tribute-attempt classification from fight dumps.
// Usage: node tools/top2/verify_draft/vroles.mjs KEY [KEY...] > out.jsonl   (reads C:/battlecode/cache/t2dump/<key>/*.json.gz + t2/<key>/index.jsonl)
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const CACHE = 'C:/battlecode/cache';
const STUDY = { pbg: '38e6d8c4', ifish: '1890540d', pantheon: '547efb5b', coo: '1570a113', cm: 'ad5474c2', nyx: '6f7fd199' };
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

function analyse(key, file, idx) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const id8 = path.basename(file).replace(/\.json\.gz$/, '').split('_').pop();
  const row = idx.get(id8);
  if (!row) return { key, file: path.basename(file), err: 'no index row' };
  const ta = row.teams.find((t) => t.side === 'a'), tb = row.teams.find((t) => t.side === 'b');
  const studyTeam = ta.teamId.startsWith(STUDY[key]) ? 0 : (tb.teamId.startsWith(STUDY[key]) ? 1 : -1);
  const st = studyTeam === 0 ? ta : tb, op = studyTeam === 0 ? tb : ta;
  const winnerIdx = d.meta.outcome === 1 ? 0 : d.meta.outcome === 2 ? 1 : -1;
  const bodies = d.meta.bodies;
  const teamOf = new Map(bodies.map((b) => [b.index, b.team]));
  const B = new Map(bodies.map((b) => [b.index, {
    body: b.index, team: b.team, type: b.type, banked: 0, nbank: 0, capGold: 0, capGems: 0, deaths: 0, gemsLost: 0, killers: [],
    kills: 0, dmgOut: 0, dmgIn: 0, dmgInAll: 0, stunsDealt: 0, bagSum: 0, bagAliveSum: 0, aliveRounds: 0, rounds: 0, bagMax: 0,
    maxHpFinal: 0, maxHpAt: {}, hpGrowth: 0, locks: 0, tributes: [], bagEnd: 0, aliveEnd: 0, deathsWithBag30: [],
  }]));
  // per-round state
  const state = new Map(); // r -> Map(body -> entry)
  for (const [r, s0, s1, cs] of d.R) {
    const m = new Map(); for (const c of cs) m.set(c[0], c); state.set(r, m);
    for (const c of cs) {
      const o = B.get(c[0]); if (!o) continue;
      o.rounds++; o.bagSum += c[6]; if (c[5]) { o.aliveRounds++; o.bagAliveSum += c[6]; }
      if (c[6] > o.bagMax) o.bagMax = c[6];
      o.maxHpFinal = c[4];
      for (const t of [300, 500, 700, 900]) if (r === t) o.maxHpAt[t] = c[4];
    }
  }
  const lastR = d.R[d.R.length - 1];
  for (const c of lastR[3]) { const o = B.get(c[0]); if (o) { o.bagEnd = c[6]; o.aliveEnd = c[5]; } }
  const bagAt = (b, r) => { for (let k = r; k >= 0; --k) { const s = state.get(k); if (s && s.has(b)) return s.get(b)[6]; } return 0; };
  // damage
  for (const [q, r, a, v, amt] of d.dmg) {
    const vt = teamOf.get(v);
    if (a >= 0 && teamOf.has(a) && teamOf.get(a) !== vt) { B.get(a).dmgOut += amt; B.get(v).dmgIn += amt; }
    if (B.has(v)) B.get(v).dmgInAll += amt;
  }
  for (const [q, r, a, v] of d.stun) if (a >= 0 && B.has(a) && teamOf.get(a) !== teamOf.get(v)) B.get(a).stunsDealt++;
  // events in q order
  const ev = d.ev.slice().sort((x, y) => x.q - y.q);
  const locks = [0, 0];
  for (const e of ev) {
    if (e.k === 'Banked') { const o = B.get(e.who); o.banked += e.gems; o.nbank++; }
    else if (e.k === 'CaptureGems') { const o = B.get(e.who); o.capGold += e.gold; o.capGems += e.gems; }
    else if (e.k === 'Death') {
      const o = B.get(e.who); o.deaths++; o.gemsLost += e.bag;
      const killer = typeof e.by === 'number' ? (teamOf.get(e.by) !== o.team ? bodies[e.by].type : 'ally:' + bodies[e.by].type) : 'camp';
      o.killers.push([e.r, killer, e.bag]);
      if (typeof e.by === 'number' && teamOf.get(e.by) !== o.team) B.get(e.by).kills++;
    } else if (e.k === 'Place altar lock') { const o = B.get(e.who); o.locks++; locks[o.team]++; }
  }
  // tribute attempts
  const stunsOn = new Map(); for (const s of d.stun) { if (!stunsOn.has(s[3])) stunsOn.set(s[3], []); stunsOn.get(s[3]).push(s); }
  const lockEv = ev.filter((e) => e.k === 'Place altar lock');
  for (let i = 0; i < ev.length; ++i) {
    const e = ev[i];
    if (e.k !== 'Submit gems') continue;
    const b = e.who, o = B.get(b), altar = e.to;
    const bag = bagAt(b, e.r);
    // was an enemy lock placed at this altar in the 60 rounds before (possible lock-attack conversion)?
    const priorLock = lockEv.filter((l) => teamOf.get(l.who) !== o.team && l.to && cheb(l.to, altar) <= 1 && l.q < e.q && e.r - l.r <= 60).length;
    let res = 'end', at = d.meta.finalRound, by = null;
    const stunNext = (stunsOn.get(b) || []).find((s) => s[0] > e.q);
    for (let j = i + 1; j < ev.length; ++j) {
      const f = ev[j];
      if (stunNext && stunNext[0] < f.q) { res = 'stun'; at = stunNext[1]; by = stunNext[2] >= 0 ? bodies[stunNext[2]].type : 'camp'; break; }
      if (f.who === b && (f.k === 'Gems submitted' || f.k === 'Banked')) { res = 'bank'; at = f.r; break; }
      if (f.who === b && f.k === 'Cancel channel') { res = 'selfcancel'; at = f.r; break; }
      if (f.k === 'Death' && f.who === b) { res = 'death'; at = f.r; by = typeof f.by === 'number' ? bodies[f.by].type : 'camp'; break; }
      if (f.k === 'Place altar lock' && teamOf.get(f.who) !== o.team && f.to && cheb(f.to, altar) <= 1) { res = 'lock'; at = f.r; by = bodies[f.who].type; break; }
      if (f.who === b && f.k === 'Submit gems') { res = 'resubmit'; at = f.r; break; }
      if (f.who === b && ['Move', 'Attack', 'Cast ability', 'Recall', 'Shop', 'Place ward', 'Consumable', 'Place altar lock'].includes(f.k)) { res = 'acted:' + f.k; at = f.r; break; }
    }
    if (res === 'end' && stunNext) { res = 'stun'; at = stunNext[1]; by = stunNext[2] >= 0 ? bodies[stunNext[2]].type : 'camp'; }
    o.tributes.push({ r: e.r, bag, need: Math.max(1, Math.ceil(bag / 10)), res, at, dt: at - e.r, by, priorLock, altar });
  }
  for (const o of B.values()) for (const k of o.killers) if (k[2] >= 30) o.deathsWithBag30.push(k);
  const out = {
    key, file: path.basename(file), id8, map: row.map, createdAt: row.createdAt, studyTeam, studyWin: winnerIdx === studyTeam ? 1 : 0,
    idxResult: st.result, opp: op.name, oppPicks: op.draftPicks, myPicks: st.draftPicks, side: st.side,
    finalRound: d.meta.finalRound, submitted: d.meta.submitted, locks,
    bodies: [...B.values()].map((o) => ({ ...o, killers: o.killers })),
  };
  return out;
}

for (const key of process.argv.slice(2)) {
  const idx = new Map();
  for (const line of fs.readFileSync(`${CACHE}/t2/${key}/index.jsonl`, 'utf8').split('\n')) {
    if (!line.trim()) continue; const m = JSON.parse(line); idx.set(m.matchId.slice(0, 8), m);
  }
  const dir = `${CACHE}/t2dump/${key}`;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json.gz')).sort()) {
    try { console.log(JSON.stringify(analyse(key, path.join(dir, f), idx))); }
    catch (err) { console.log(JSON.stringify({ key, file: f, err: String(err.message || err) })); }
  }
}
