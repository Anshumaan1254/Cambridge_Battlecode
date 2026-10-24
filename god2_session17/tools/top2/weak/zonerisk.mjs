#!/usr/bin/env node
// Zone presence and risk (an_weak): per study-team fightdump dump, for the study team (S) and its opponent (O): alive body-rounds in the
// own / mid / enemy zone (walking-distance share as in wx.mjs) for rounds 20..min(final, 1200), champion-kill deaths in each zone, and the
// same split for bodies alone (no ally within 6) -> deaths per 100 body-rounds by zone and isolation.
//   node tools/top2/weak/zonerisk.mjs dump.json.gz...
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const TEAMS = { pbg: '38e6d8c4', ifish: '1890540d', cm: 'ad5474c2', pantheon: '547efb5b', coo: '1570a113', nyx: '6f7fd199' };
const GEO = new Map();
for (const l of fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n')) { if (!l.trim()) continue; const g = JSON.parse(l); GEO.set(g.map, g); }
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
  const row = idx(key).get(mm[2]); const geo = GEO.get(mm[1]); if (!row || !geo) continue;
  const me = row.teams.find((t) => t.teamId.startsWith(TEAMS[key]));
  const S = me.side === 'a' ? 0 : 1;
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const teamOf = (i) => d.meta.bodies[i]?.team;
  const PM = new Map(); for (const e of d.R) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(e[0], m); }
  const W = geo.W, H = geo.H;
  const r1 = PM.get(1); const c0 = [...r1.values()].filter((c) => teamOf(c[0]) === 0); const cx = c0.reduce((a, c) => a + c[1], 0) / c0.length, cy = c0.reduce((a, c) => a + c[2], 0) / c0.length;
  const sA = geo.spawnA[0]; const sB = geo.spawnB[0];
  const swap = cheb(cx, cy, sA[0], sA[1]) > cheb(cx, cy, sB[0], sB[1]);
  const zone = (t, x, y) => { if (x < 0 || y < 0 || x >= W || y >= H) return null; const a = geo.dA[y * W + x], b = geo.dB[y * W + x]; if (a < 0 || b < 0) return null; const own = ((t === 0) !== swap) ? a : b, en = ((t === 0) !== swap) ? b : a; const f = own / (own + en || 1); return f < 0.4 ? 'own' : f > 0.6 ? 'enemy' : 'mid'; };
  const out = { file: base, key, S, win: me.result === 'win' ? 1 : 0, T: {} };
  for (const t of [S, 1 - S]) out.T[t === S ? 'S' : 'O'] = { own: [0, 0, 0, 0], mid: [0, 0, 0, 0], enemy: [0, 0, 0, 0] }; // [rounds, deaths, rounds alone, deaths alone]
  const deathsAt = new Map(); for (const e of d.ev) if (e.k === 'Death' && typeof e.by === 'number' && teamOf(e.by) !== e.team) { if (!deathsAt.has(e.r)) deathsAt.set(e.r, []); deathsAt.get(e.r).push(e.who); }
  const final = Math.min(d.meta.finalRound, 1200);
  for (let r = 20; r <= final; r++) {
    const m = PM.get(r - 1); if (!m) continue; const L = [...m.values()].filter((c) => c[5]);
    const dead = new Set(deathsAt.get(r) || []);
    for (const c of L) {
      const t = teamOf(c[0]); const z = zone(t, c[1], c[2]); if (!z) continue;
      const alone = !L.some((o) => o[0] !== c[0] && teamOf(o[0]) === t && cheb(o[1], o[2], c[1], c[2]) <= 6);
      const X = out.T[t === S ? 'S' : 'O'][z]; X[0]++; if (alone) X[2]++; if (dead.has(c[0])) { X[1]++; if (alone) X[3]++; }
    }
  }
  console.log(JSON.stringify(out));
}
