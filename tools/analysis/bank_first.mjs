// usage: node tools/analysis/bank_first.mjs DIR_OR_FILE... (LEGEND_TRACE bundles) : capture-recalls whose bag is then banked from spawn: actual rounds until walking to the next
// target vs "bank from the capture tile first, then recall (or walk on)"
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay, findEngineWasms } from '../replay/decode.mjs';
import { WASI } from 'node:wasi';
process.removeAllListeners('warning');
const T_TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
async function mapGrid(buf) {
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const inst = await WebAssembly.instantiate(await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0])), { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst); const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
  const p = X.Engine_Malloc(buf.length); new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  X.Game_FromReplayFileBytes(p, buf.length, out); const g = dv().getBigUint64(out, true);
  X.Game_GetBitboardMetadata(g, out); const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
  X.Game_GetSymmetry(g, out); const sym = dv().getInt32(out, true);
  X.Game_GetTeamASpawnArea(g, out); const sp = [0, 4, 8, 12].map(o => dv().getInt32(out + o, true));
  const tile = (fn, x, y) => { X[fn](g, x, y, out); return dv().getUint8(out) !== 0; };
  const block = new Uint8Array(w * h), altars = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { if (tile('Game_GetWall', x, y) || tile('Game_GetHole', x, y)) block[y * w + x] = 1; if (tile('Game_GetAltar', x, y)) { block[y * w + x] = 1; altars.push([x, y]); } }
  const mirror = (x, y) => (sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y]);
  const spawnA = new Uint8Array(w * h), spawnB = new Uint8Array(w * h), sa = [], sb = [];
  for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) { spawnA[y * w + x] = 1; sa.push([x, y]); const [mx, my] = mirror(x, y); spawnB[my * w + mx] = 1; sb.push([mx, my]); }
  return { w, h, block, spawnA, spawnB, sa, sb, altars };
}
function bfs(grid, blocked, roots) {
  const { w, h } = grid; const d = new Int32Array(w * h).fill(1 << 20); const q = new Int32Array(w * h); let qh = 0, qt = 0;
  for (const [x, y] of roots) { const i = y * w + x; if (d[i]) { d[i] = 0; q[qt++] = i; } }
  while (qh < qt) { const i = q[qh++], x = i % w, y = (i / w) | 0;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { if (!dx && !dy) continue; const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue; const j = ny * w + nx; if (blocked[j] || d[j] <= d[i] + 1) continue; d[j] = d[i] + 1; q[qt++] = j; } }
  return d;
}
const files = process.argv.slice(2).flatMap(p => fs.statSync(p).isDirectory() ? fs.readdirSync(p).filter(f => f.endsWith('.repl26a')).map(f => path.join(p, f)) : [p]);
const A = { n: 0, actual: 0, alt: 0, better10: 0, save10: 0 };
for (const f of files) {
  const raw = fs.readFileSync(f); const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const text = unwrapReplay(raw, our ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const turns = {}, G = [];
  for (const l of text.split('\n')) {
    let m = l.match(/G id=(\d+) .*tiles=(.*)$/); if (m) { G[+m[1]] = m[2].trim().split(';').filter(Boolean).map(s => s.split(',').map(Number)); continue; }
    m = l.match(/T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\)/); if (m) (turns[T_TYPES[+m[2]]] ||= {})[+m[1]] = { task: +m[3], g: +m[4], pos: [+m[5], +m[6]] }; }
  const rep = unwrapReplay(raw); const d = await decode(rep, { every: 1 }); const grid = await mapGrid(rep);
  const blocked = new Uint8Array(grid.w * grid.h); const es = our ? grid.spawnA : grid.spawnB;
  for (let i = 0; i < blocked.length; i++) blocked[i] = grid.block[i] || es[i];
  const gf = G.map(t => bfs(grid, blocked, t)); const gd = (g, p) => gf[g][p[1] * grid.w + p[0]];
  // altar approach: neighbours of altars
  const approach = []; for (const [x, y] of grid.altars) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const nx = x + dx, ny = y + dy; if (nx >= 0 && ny >= 0 && nx < grid.w && ny < grid.h && !blocked[ny * grid.w + nx]) approach.push([nx, ny]); }
  const perAltar = grid.altars.map(([x, y]) => { const tiles = []; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const nx = x + dx, ny = y + dy; if (nx >= 0 && ny >= 0 && nx < grid.w && ny < grid.h && !blocked[ny * grid.w + nx]) tiles.push([nx, ny]); } return { tiles, f: bfs(grid, blocked, tiles) }; });
  const af = bfs(grid, blocked, approach); const ad = (p) => af[p[1] * grid.w + p[0]];
  const spawnTiles = our ? grid.sb : grid.sa; const sf = bfs(grid, blocked, spawnTiles); const sd = (p) => sf[p[1] * grid.w + p[0]];
  const ev = d.events.filter(e => e.team === our);
  let pn = 0, pa = 0, pb = 0;
  for (const b of d.meta.bodies.filter(b => b.team === our)) {
    const T = turns[b.type] || {}; const mine = ev.filter(e => e.who === b.index);
    for (const c of mine.filter(e => e.k === 'CaptureGems')) {
      const rec = mine.find(e => e.k === 'Recall' && e.r >= c.r - 6 && e.r <= c.r); if (!rec) continue;
      const capPos = T[rec.r] ? T[rec.r].pos : null; if (!capPos) continue;
      const sub = mine.find(e => e.k === 'Submit gems' && e.r > c.r - 1 && e.r < c.r + 80); if (!sub) continue;
      const bk = mine.find(e => e.k === 'Banked' && e.r >= sub.r);
      // next target after the submit
      let g2 = -1, r2 = -1, from = null;
      for (let r = sub.r + 1; r <= sub.r + 80; r++) { const t = T[r]; if (t && t.task >= 1 && t.task <= 3 && t.g >= 0) { g2 = t.g; r2 = r; const p = T[r - 1]; from = p ? p.pos : t.pos; break; } }
      if (g2 < 0) continue;
      // was there another capture between? skip if so
      if (mine.some(e => e.k === 'CaptureGems' && e.r > c.r && e.r < sub.r)) continue;
      const S = (bk ? bk.r : sub.r + 1) - sub.r;
      const actual = (r2 - c.r) + gd(g2, from);
      const dA = ad(capPos);
      // nearest altar from the capture tile, then the walk on from it (or recall home and walk out)
      let bi = -1, bd = 1 << 20; for (let i = 0; i < perAltar.length; i++) { const v = perAltar[i].f[capPos[1] * grid.w + capPos[0]]; if (v < bd) bd = v, bi = i; }
      if (bi < 0 || !G[g2]) continue;
      const onFromAltar = Math.min(...perAltar[bi].tiles.map(t => gd(g2, t)));
      const alt = bd + S + Math.min(6 + gd(g2, spawnTiles[Math.floor(spawnTiles.length / 2)]), onFromAltar);
      A.n++; A.actual += actual; A.alt += Math.min(alt, actual); pn++; pa += actual; pb += Math.min(alt, actual);
      if (actual - alt >= 10) A.better10++, A.save10 += actual - alt;
    }
  }
  console.log(path.basename(f).padEnd(34), 'recall->bank-from-home trips', pn, 'actual', (pa / Math.max(1, pn)).toFixed(1), 'best-of-both', (pb / Math.max(1, pn)).toFixed(1));
}
console.log(`TOTAL ${A.n} trips; rounds from capture to walking toward the next target ${(A.actual / A.n).toFixed(1)}, with bank-first when cheaper ${(A.alt / A.n).toFixed(1)}; bank-first saves >=10 rounds in ${A.better10} (${A.save10} rounds)`);
