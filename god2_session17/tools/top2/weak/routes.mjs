#!/usr/bin/env node
// Opening routes (an_weak): per study-team game (fightdump dump), every study body's position at checkpoints r5..r150 and the first
// three camp groups each body hit (round, group centre), the team's first three captures (round, tile), the first ward tiles, and the
// opponent's positions too. Used to test whether the same team on the same map and side repeats its opening across opponents.
//   node tools/top2/weak/routes.mjs dump.json.gz...   -> one JSON line per game
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
const CPS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 150, 200];
const IDX = new Map();
function idx(key) {
  if (IDX.has(key)) return IDX.get(key);
  const m = new Map(); const p = `C:/battlecode/cache/t2/${key}/index.jsonl`;
  if (fs.existsSync(p)) for (const l of fs.readFileSync(p, 'utf8').split('\n')) { if (!l.trim()) continue; const r = JSON.parse(l); m.set(r.matchId.slice(0, 8), r); }
  IDX.set(key, m); return m;
}
for (const file of process.argv.slice(2)) {
  const base = path.basename(file); const key = path.basename(path.dirname(file));
  const mm = base.match(/^(.*)_([0-9a-f]{8})\.json\.gz$/); if (!mm) continue;
  const row = idx(key).get(mm[2]); if (!row) continue;
  const me = row.teams.find((t) => t.teamId.startsWith(TEAMS[key])); const op = row.teams.find((t) => !t.teamId.startsWith(TEAMS[key]));
  const S = me.side === 'a' ? 0 : 1;
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const PM = new Map(); for (const e of d.R) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(e[0], m); }
  const camps = d.meta.camps;
  const out = { file: base, key, map: mm[1], S, side: me.side, win: me.result === 'win' ? 1 : 0, opp: op.name, draft: me.draftPicks, odraft: op.draftPicks, bodies: {} };
  for (const t of [S, 1 - S]) for (const b of d.meta.bodies.filter((x) => x.team === t)) {
    const pos = CPS.map((r) => { const c = PM.get(r)?.get(b.index); return c && c[5] ? [c[1], c[2]] : null; });
    const hits = []; const seen = new Set();
    for (const x of d.cdmg) { if (x[2] !== b.index) continue; const c = camps.find((k) => k.index === x[3]); if (!c) continue; const k = `${c.x},${c.y}`; if (seen.has(k)) continue; seen.add(k); hits.push([x[1], c.x, c.y, c.type]); if (hits.length >= 3) break; }
    const wards = d.ev.filter((e) => e.k === 'Place ward' && e.who === b.index).slice(0, 3).map((e) => [e.r, e.to[0], e.to[1]]);
    out.bodies[b.index] = { team: t === S ? 'S' : 'O', ty: b.type, pos, hits, wards };
  }
  out.caps = { S: [], O: [] };
  for (const e of d.ev) if (e.k === 'CaptureGems') { const k = d.meta.bodies[e.who].team === S ? 'S' : 'O'; if (out.caps[k].length < 4) out.caps[k].push([e.r, e.at[0], e.at[1], e.gems, d.meta.bodies[e.who].type]); }
  out.firstKill = null;
  for (const e of d.ev) if (e.k === 'Death' && typeof e.by === 'number') { out.firstKill = [e.r, d.meta.bodies[e.who].team === S ? 'S died' : 'O died', d.meta.bodies[e.who].type, e.at]; break; }
  console.log(JSON.stringify(out));
}
