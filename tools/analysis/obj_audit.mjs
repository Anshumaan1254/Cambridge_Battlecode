// Objective audit (agent obj, session 3): for each gem-source cluster (non-gold camps within Chebyshev 2 of each other, size >= minsize),
// per team: hits on it, share of its HP loss, captures (gems), bodies near it per round, deaths near/far,
// and what the team's bodies did meanwhile (near objective / own half / enemy half / dead).
//   node objaudit.mjs REPLAY [--min 100] [--win 200]
import fs from 'fs';
import { decode } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const f = args.find((a) => a.endsWith('.repl26a'));
const minGems = args.includes('--min') ? +args[args.indexOf('--min') + 1] : 100;
const WIN = args.includes('--win') ? +args[args.indexOf('--win') + 1] : 200;
const d = await decode(fs.readFileSync(f), { every: 1 });
const camps = d.meta.camps;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
// clusters
const src = camps.filter((c) => c.type !== 'gold');
const cl = []; const of = {};
for (const c of src) {
  let k = cl.findIndex((K) => K.some((o) => cheb([o.x, o.y], [c.x, c.y]) <= 2));
  if (k < 0) { k = cl.length; cl.push([]); }
  cl[k].push(c); of[c.index] = k;
}
const big = cl.map((K, i) => ({ i, K, hp: K.reduce((s, c) => s + c.hp, 0), tiles: K.map((c) => [c.x, c.y]) })).filter((x) => x.K.length >= 2 || x.K.some((c) => c.type === 'monolith'));
const near = (p, B, r) => B.tiles.some((t) => cheb(p, t) <= r);
console.log(`${f.split('/').pop()} outcome ${d.meta.outcome} final r${d.meta.finalRound} sub ${d.meta.submitted}`);
for (const B of big) {
  const types = {}; B.K.forEach((c) => types[c.type] = (types[c.type] || 0) + 1);
  const cen = B.tiles.reduce((s, t) => [s[0] + t[0] / B.tiles.length, s[1] + t[1] / B.tiles.length], [0, 0]).map(Math.round);
  console.log(`== cluster ${B.i} at ${cen} ${JSON.stringify(types)} hp ${B.hp}`);
  const tileSet = new Set(B.tiles.map((t) => t.join(',')));
  const hits = [{}, {}];
  const hitsByRound = {};
  for (const e of d.events) if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to && tileSet.has(e.to.join(',')) && e.team !== undefined) {
    hitsByRound[e.r] = hitsByRound[e.r] || [0, 0]; hitsByRound[e.r][e.team]++;
  }
  // hp loss per round
  const idx = B.K.map((c) => camps.indexOf(c));
  const dmg = [0, 0]; let firstHit = [null, null];
  for (let i = 1; i < d.rounds.length; i++) {
    const r = d.rounds[i], p = d.rounds[i - 1];
    let loss = 0; for (const j of idx) loss += Math.max(0, p.campHp[j] - r.campHp[j]);
    const h = hitsByRound[r.r]; if (!h || !loss) continue;
    for (const t of [0, 1]) { if (h[t] && firstHit[t] === null) firstHit[t] = r.r; dmg[t] += loss * h[t] / (h[0] + h[1]); }
  }
  console.log(`   damage share A ${dmg[0].toFixed(0)} B ${dmg[1].toFixed(0)}; first hit A r${firstHit[0]} B r${firstHit[1]}`);
  const caps = d.events.filter((e) => e.k === 'CaptureGems' && e.gems >= minGems && near(e.at, B, 1));
  console.log(`   captures: ${caps.map((e) => `r${e.r} ${'AB'[e.team]} ${e.champ} ${e.gems}g`).join(', ') || 'none'}`);
  const deaths = d.events.filter((e) => e.k === 'Death');
  const dn = [0, 0], df = [0, 0];
  for (const e of deaths) (near(e.at, B, 8) ? dn : df)[e.team]++;
  console.log(`   deaths near (<=8) A ${dn[0]} B ${dn[1]}; elsewhere A ${df[0]} B ${df[1]}`);
  // per window activity: bodies near (<=6), dead, mean
  console.log(`   window   nearA nearB deadA deadB  hitsA hitsB  dthA dthB  bankA bankB`);
  for (let w = 0; w < d.meta.finalRound; w += WIN) {
    const R = d.rounds.filter((r) => r.r >= w && r.r < w + WIN);
    const nA = [0, 0], dd = [0, 0];
    for (const r of R) for (const c of r.ch) { if (!c[7]) dd[c[1]]++; else if (near([c[3], c[4]], B, 6)) nA[c[1]]++; }
    const hs = [0, 0]; for (let r = w; r < w + WIN; r++) if (hitsByRound[r]) { hs[0] += hitsByRound[r][0]; hs[1] += hitsByRound[r][1]; }
    const dt = [0, 0]; deaths.filter((e) => e.r >= w && e.r < w + WIN).forEach((e) => dt[e.team]++);
    const bk = [0, 0]; d.events.filter((e) => e.k === 'Banked' && e.r >= w && e.r < w + WIN).forEach((e) => bk[e.team] += e.gems);
    const n = Math.max(1, R.length);
    console.log(`   ${String(w).padStart(4)}-${String(w + WIN).padEnd(4)} ${(nA[0] / n).toFixed(1).padStart(5)} ${(nA[1] / n).toFixed(1).padStart(5)} ${(dd[0] / n).toFixed(1).padStart(5)} ${(dd[1] / n).toFixed(1).padStart(5)}  ${String(hs[0]).padStart(5)} ${String(hs[1]).padStart(5)}  ${String(dt[0]).padStart(4)} ${String(dt[1]).padStart(4)}  ${String(bk[0]).padStart(5)} ${String(bk[1]).padStart(5)}`);
  }
}
