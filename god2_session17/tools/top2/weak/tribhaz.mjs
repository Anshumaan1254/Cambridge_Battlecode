#!/usr/bin/env node
// Tribute cancel hazard (an_weak): for every tribute channel with bag >= MIN (env BAGMIN, default 100) of either team in a study-team
// fightdump dump, one record per channel round: distance to the nearest living enemy champion (99 if none), champion damage and camp
// damage taken that round, enemy stunner (Prism/Ryth/Marcella/Tavi/Cassi/HoR/Ren) within 5, and how the channel ended in that round
// (none / self = Cancel channel or another action / stun / lock / death / done). Output: one JSON line per game
// {file, key, S, win, ch: [{team, ty, bag, need, rows: [[dist, champDmg, campDmg, stunnerNear, endCode], ...]}]}.
//   node tools/top2/weak/tribhaz.mjs dump.json.gz...
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
const MIN = +(process.env.BAGMIN || 100);
const STUN = new Set(['Prism', 'Ryth', 'Marcella', 'Tavi', 'Cassi', 'HeartOfRuin', 'Ren']);
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
  const evBy = new Map(); for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
  const locks = d.ev.filter((e) => e.k === 'Place altar lock');
  const ch = [];
  for (const e of d.ev) {
    if (e.k !== 'Submit gems') continue;
    const b = e.who, t = teamOf(b); const bag = PM.get(e.r)?.get(b)?.[6] ?? 0; if (bag < MIN) continue;
    const nx = (evBy.get(b) || []).find((x) => x.q > e.q && x.k !== 'Banked');
    const rEnd = nx ? nx.r : d.meta.finalRound; const qEnd = nx ? nx.q : 1e12;
    let endK = 'open';
    if (nx) endK = nx.k === 'Gems submitted' ? 'done' : nx.k === 'Death' ? 'death' : 'self';
    if (endK === 'self') {
      if (locks.some((L) => L.q > e.q && L.q <= qEnd && teamOf(L.who) !== t && cheb(L.to[0], L.to[1], e.to[0], e.to[1]) === 0)) endK = 'lock';
      else if (d.stun.some((s) => s[3] === b && s[0] > e.q && s[0] <= qEnd)) endK = 'stun';
    }
    const rows = [];
    for (let r = e.r; r <= rEnd; r++) {
      const m = PM.get(r); const meC = m?.get(b); if (!meC) continue;
      let dist = 99, sn = 0;
      for (const c of m.values()) if (c[5] && teamOf(c[0]) !== t) { const dd = cheb(c[1], c[2], meC[1], meC[2]); if (dd < dist) dist = dd; if (dd <= 5 && STUN.has(tyOf(c[0]))) sn = 1; }
      let cd = 0, kd = 0;
      for (const x of d.dmg) if (x[1] === r && x[3] === b && x[0] > e.q && x[0] <= qEnd) { if (x[2] >= 0) cd += x[4]; else kd += x[4]; }
      rows.push([dist, cd, kd, sn, r === rEnd ? endK : '']);
    }
    ch.push({ team: t, ty: tyOf(b), bag, need: Math.max(1, Math.ceil(bag / 10)), r: e.r, rows });
  }
  console.log(JSON.stringify({ file: base, key, S, win: me.result === 'win' ? 1 : 0, ch }));
}
