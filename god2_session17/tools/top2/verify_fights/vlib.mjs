// Verify-fights shared loader (independent re-measure of experiments/top2/an_fights.md claims).
// loadGame(gameRow, geo) -> G with per-round dense arrays (end-of-round state), events by round, champion hits, deaths,
// spawn / altar geometry and helpers. Rounds are indexed 1..final (R[0], the pre-game snapshot, is round 0).
import fs from 'node:fs';
import zlib from 'node:zlib';

export function loadGeo(file) {
  const geo = {};
  for (const l of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!l.trim()) continue;
    const g = JSON.parse(l);
    const W = g.W, H = g.H;
    const pass = new Uint8Array(W * H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const c = g.grid[y][x]; pass[y * W + x] = (c === '.' || c === '"') ? 1 : 0; }
    // walking distance (8-connected) to the nearest tile from which a tribute can start (Chebyshev 1 of an altar)
    const dAlt = new Int32Array(W * H).fill(-1); const q = [];
    for (const [ax, ay] of g.altars) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const x = ax + dx, y = ay + dy; if (x < 0 || y < 0 || x >= W || y >= H || !pass[y * W + x]) continue;
      if (dAlt[y * W + x] < 0) { dAlt[y * W + x] = 0; q.push(y * W + x); }
    }
    for (let h = 0; h < q.length; h++) {
      const k = q[h], x = k % W, y = (k - x) / W;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue; const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H || !pass[ny * W + nx] || dAlt[ny * W + nx] >= 0) continue;
        dAlt[ny * W + nx] = dAlt[k] + 1; q.push(ny * W + nx);
      }
    }
    const spawn = [new Set(g.spawnA.map(([x, y]) => y * W + x)), new Set(g.spawnB.map(([x, y]) => y * W + x))];
    const spc = [g.spawnA, g.spawnB].map((s) => [s.reduce((a, p) => a + p[0], 0) / s.length, s.reduce((a, p) => a + p[1], 0) / s.length]);
    geo[g.map] = { W, H, altars: g.altars.map((a) => [a[0], a[1]]), spawn, spc, dAlt, pass, grid: g.grid };
  }
  return geo;
}

export const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));

export function loadGame(row, geo) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(row.dump)));
  const gm = geo[row.map];
  const bodies = d.meta.bodies;
  const nb = Math.max(...bodies.map((b) => b.index)) + 1;
  const team = new Int8Array(nb).fill(-1), type = new Array(nb).fill('?');
  for (const b of bodies) { team[b.index] = b.team; type[b.index] = b.type; }
  const final = d.meta.finalRound;
  const NR = final + 2;
  const X = new Int16Array(NR * nb).fill(-1), Y = new Int16Array(NR * nb).fill(-1);
  const HP = new Float32Array(NR * nb), MHP = new Float32Array(NR * nb), AL = new Uint8Array(NR * nb), GEM = new Int32Array(NR * nb);
  const GOLD = new Int32Array(NR * nb), KIL = new Int32Array(NR * nb), STN = new Uint8Array(NR * nb);
  const SUB = [new Int32Array(NR), new Int32Array(NR)];
  const put = (r, rec) => {
    SUB[0][r] = rec[1]; SUB[1][r] = rec[2];
    for (const c of rec[3]) {
      const k = r * nb + c[0];
      X[k] = c[1]; Y[k] = c[2]; HP[k] = c[3]; MHP[k] = c[4]; AL[k] = c[5]; GEM[k] = c[6]; GOLD[k] = c[7]; KIL[k] = c[8]; STN[k] = c[9];
    }
  };
  put(0, d.R[0]);
  let last = 0;
  for (let i = 1; i < d.R.length; i++) { const r = d.R[i][0]; if (r <= 0 || r >= NR) continue; put(r, d.R[i]); last = Math.max(last, r); }
  const evBy = Array.from({ length: NR }, () => []);
  for (const e of d.ev) if (e.r >= 0 && e.r < NR) evBy[e.r].push(e);
  // champion-vs-champion hits (exclude camps and Ren reflect a == v)
  const hits = [];
  for (const h of d.dmg) {
    const [q, r, a, v, amt, kind, slot] = h;
    if (a < 0 || a === v || team[a] === team[v]) continue;
    hits.push({ q, r, a, v, amt, kind, slot });
  }
  hits.sort((p, s) => p.q - s.q);
  const hitsBy = Array.from({ length: NR }, () => []);
  for (const h of hits) if (h.r < NR) hitsBy[h.r].push(h);
  const stuns = d.stun.filter((s) => s[2] >= 0 && team[s[2]] !== team[s[3]]).map(([q, r, a, v]) => ({ q, r, a, v }));
  const deaths = d.ev.filter((e) => e.k === 'Death');
  const campHitsBy = Array.from({ length: NR }, () => []);
  for (const c of d.cdmg) if (c[1] < NR) campHitsBy[c[1]].push({ q: c[0], r: c[1], a: c[2], camp: c[3], amt: c[4] });
  const G = {
    row, d, gm, nb, team, type, final, last, NR, X, Y, HP, MHP, AL, GEM, GOLD, KIL, STN, SUB, evBy, hits, hitsBy, stuns, deaths, campHitsBy,
    k: (r, b) => r * nb + b,
    x: (r, b) => X[r * nb + b], y: (r, b) => Y[r * nb + b], hp: (r, b) => HP[r * nb + b], mhp: (r, b) => MHP[r * nb + b],
    alive: (r, b) => AL[r * nb + b] === 1, gems: (r, b) => GEM[r * nb + b],
    dist: (r, a, b) => cheb(X[r * nb + a], Y[r * nb + a], X[r * nb + b], Y[r * nb + b]),
    onSpawn: (r, b) => gm.spawn[team[b]].has(Y[r * nb + b] * gm.W + X[r * nb + b]),
    onSpawnXY: (t, x, y) => gm.spawn[t].has(y * gm.W + x),
    dAltar: (x, y) => (x >= 0 && y >= 0 && x < gm.W && y < gm.H) ? gm.dAlt[y * gm.W + x] : -1,
    dSpawnC: (t, x, y) => cheb(x, y, Math.round(gm.spc[t][0]), Math.round(gm.spc[t][1])),
  };
  G.S = row.sidx; G.O = 1 - row.sidx;
  G.sb = []; G.ob = [];
  for (let b = 0; b < nb; b++) if (team[b] === G.S) G.sb.push(b); else if (team[b] === G.O) G.ob.push(b);
  return G;
}

export function readGames(file, filt) {
  const games = JSON.parse(fs.readFileSync(file, 'utf8'));
  return filt ? games.filter(filt) : games;
}
