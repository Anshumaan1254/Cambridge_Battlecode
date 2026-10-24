#!/usr/bin/env node
// Where teams wait: runs of >= 10 rounds in which a living body neither moves nor attacks / casts / captures / banks, off its own spawn
// (recall spam does not break a run). Per team: runs, rounds, and the share of hold rounds next to a camp tile (Chebyshev <= 2), next to
// an altar (<= 3), in the middle zone (walking-distance share 0.4-0.6), in the enemy zone (> 0.6), and the share whose camp group
// next to the body was captured by the holder's team within 20 rounds after the hold ended (waiting for a respawn).
//   node tools/top2/playbooks/pb_holds.mjs dump.json.gz...   -> one JSON line per game
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const GEO = new Map(fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => { const g = JSON.parse(l); return [g.map, g]; }));
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
for (const file of process.argv.slice(2)) {
  try {
    const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
    const name = path.basename(file).replace(/\.json\.gz$/, '');
    const g = GEO.get(name.replace(/_[0-9a-f]{8}$/, ''));
    const W = d.meta.width, H = d.meta.height, final = d.meta.finalRound;
    const bodies = d.meta.bodies;
    const teamOf = (i) => bodies[i].team;
    const sp0 = d.R[0][3];
    const spc = [0, 1].map((t) => { const b = sp0.filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
    const pass = (arr, x, y) => x >= 0 && y >= 0 && x < W && y < H && arr[y * W + x] >= 0;
    const dist = (arr, x, y) => { if (pass(arr, x, y)) return arr[y * W + x]; let b = 1e9; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (pass(arr, x + dx, y + dy)) b = Math.min(b, arr[(y + dy) * W + x + dx] + 1); return b >= 1e9 ? -1 : b; };
    const fT = (t, x, y) => { let a = g ? dist(g.dA, x, y) : -1, b = g ? dist(g.dB, x, y) : -1; if (a < 0 || b < 0) { a = Math.hypot(x - spc[0][0], y - spc[0][1]); b = Math.hypot(x - spc[1][0], y - spc[1][1]); } const v = a + b > 0 ? a / (a + b) : 0.5; return t === 0 ? v : 1 - v; };
    const altars = g ? g.altars.map((a) => [a[0], a[1]]) : [];
    const camps = d.meta.camps;
    const S = new Array(final + 1);
    for (let k = 1; k < d.R.length; k++) S[d.R[k][0]] = d.R[k];
    for (let r = 1; r <= final; r++) if (!S[r]) S[r] = S[r - 1];
    const act = new Set();
    for (const x of d.dmg) if (x[2] >= 0) act.add(x[2] * 100000 + x[1]);
    for (const x of d.cdmg) act.add(x[2] * 100000 + x[1]);
    for (const e of d.ev) if (e.who !== undefined && ['CaptureGems', 'Banked', 'Submit gems', 'Attack', 'Cast ability', 'Place ward', 'Place altar lock', 'Shop'].includes(e.k)) act.add(e.who * 100000 + e.r);
    const caps = d.ev.filter((e) => e.k === 'CaptureGems');
    const out = { file: name, t: [0, 1].map(() => ({ runs: 0, rounds: 0, camp: 0, altar: 0, mid: 0, their: 0, respawnCap: 0 })) };
    for (const b of bodies) {
      const t = b.team; let r0 = null, x0 = 0, y0 = 0;
      const close = (r) => {
        const len = r - r0;
        if (r0 !== null && len >= 10) {
          const T = out.t[t]; T.runs++; T.rounds += len;
          const nearCamp = camps.filter((c) => cheb(c.x, c.y, x0, y0) <= 2);
          if (nearCamp.length) T.camp += len;
          if (altars.some((a) => cheb(a[0], a[1], x0, y0) <= 3)) T.altar += len;
          const f = fT(t, x0, y0);
          if (f >= 0.4 && f <= 0.6) T.mid += len; else if (f > 0.6) T.their += len;
          if (nearCamp.length && caps.some((e) => e.team === t && e.r >= r && e.r <= r + 20 && cheb(e.at[0], e.at[1], x0, y0) <= 4)) T.respawnCap += len;
        }
        r0 = null;
      };
      for (let r = 2; r <= final; r++) {
        const c = S[r][3].find((c) => c[0] === b.index), p = S[r - 1][3].find((c) => c[0] === b.index);
        const still = c && p && c[5] && p[5] && c[1] === p[1] && c[2] === p[2] && cheb(c[1], c[2], spc[t][0], spc[t][1]) > 2.6 && !act.has(b.index * 100000 + r);
        if (still) { if (r0 === null) { r0 = r; x0 = c[1]; y0 = c[2]; } }
        else close(r);
      }
      close(final + 1);
    }
    console.log(JSON.stringify(out));
  } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); }
}
