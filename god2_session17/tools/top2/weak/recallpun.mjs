#!/usr/bin/env node
// Recall punishment (an_weak): every recall start (skipping recall-spam: a body that issued Recall in the previous round) by either team in
// a study-team fightdump dump, with the nearest enemy champion's distance at the start, the recaller's hp share, whether an enemy
// champion damaged it within the next 5 rounds, and the outcome within 8 rounds (home = arrived on its spawn, dead, still away).
// One JSON line per game: {file, key, S, win, rec: [[team(S/O), type, dist, hpShare, damaged(0/1), outcome], ...]}
//   node tools/top2/weak/recallpun.mjs dump.json.gz...
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
  const spawn = new Map(); const m1 = PM.get(1); if (m1) for (const c of m1.values()) spawn.set(c[0], [c[1], c[2]]);
  const recBy = new Map(); for (const e of d.ev) if (e.k === 'Recall') { if (!recBy.has(e.who)) recBy.set(e.who, new Set()); recBy.get(e.who).add(e.r); }
  const dmgOn = new Map(); for (const x of d.dmg) if (x[2] >= 0 && teamOf(x[2]) !== teamOf(x[3])) { if (!dmgOn.has(x[3])) dmgOn.set(x[3], new Set()); dmgOn.get(x[3]).add(x[1]); }
  const rec = [];
  for (const [b, rs] of recBy) {
    const t = teamOf(b); const sp = spawn.get(b);
    for (const r of rs) {
      if (rs.has(r - 1)) continue;
      const p = PM.get(r - 1)?.get(b); if (!p || !p[5] || !sp) continue;
      if (cheb(p[1], p[2], sp[0], sp[1]) <= 3) continue; // on/near spawn
      let dist = 99; const m = PM.get(r - 1); for (const c of m.values()) if (c[5] && teamOf(c[0]) !== t) dist = Math.min(dist, cheb(c[1], c[2], p[1], p[2]));
      let damaged = 0; for (let k = r; k <= r + 5; k++) if (dmgOn.get(b)?.has(k)) damaged = 1;
      let res = 'away';
      for (let k = r; k <= r + 8; k++) { const c = PM.get(k)?.get(b); if (!c) continue; if (!c[5]) { res = 'dead'; break; } if (cheb(c[1], c[2], sp[0], sp[1]) <= 3) { res = 'home'; break; } }
      rec.push([t === S ? "S" : "O", tyOf(b), dist, +(p[3] / p[4]).toFixed(2), damaged, res, r]);
    }
  }
  console.log(JSON.stringify({ file: base, key, S, win: me.result === 'win' ? 1 : 0, rec }));
}
