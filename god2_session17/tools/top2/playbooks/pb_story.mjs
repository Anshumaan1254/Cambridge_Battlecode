#!/usr/bin/env node
// One game as a phase story for team T, from a tools/live/fightdump.mjs dump (fast; no engine). Every K rounds (K1 until r300, K2 after):
//   score T-O | team T clusters: [types]@zone(mean f, walking-distance share own 0 .. enemy 1) hp% bags | the opponent's clusters
//   | window events of both teams: captures (n, gems, camp classes, zones), banks (n, gems, big ones with the banker), deaths / kills
//   (victim, bag, zone), completed recalls, altar locks, objective (monolith / golem) damage and captures.
//   node tools/top2/playbooks/pb_story.mjs dump.json.gz T [K1=50] [K2=100]
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const [file, Ts, K1s, K2s] = process.argv.slice(2);
const T = +Ts, K1 = +(K1s || 50), K2 = +(K2s || 100);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const name = path.basename(file).replace(/\.json\.gz$/, '');
const map = name.replace(/_[0-9a-f]{8}$/, '');
const geo = fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)).find((g) => g.map === map);
const W = d.meta.width, H = d.meta.height, final = d.meta.finalRound;
const bodies = d.meta.bodies;
const teamOf = (i) => bodies[i].team;
const short = (t) => ({ VesperVale: 'Ves', HeartOfRuin: 'HoR', Marcella: 'Mar', Vendetta: 'Vnd', Prism: 'Pri', Ryth: 'Ryt', Willow: 'Wil', Tavi: 'Tav', Cassi: 'Cas', Issac: 'Iss', Stellar: 'Ste', Varg: 'Var', Ren: 'Ren' }[t] || t);
const cheb = (a, b, c, e) => Math.max(Math.abs(a - c), Math.abs(b - e));
const sp0 = d.R[0][3];
const spc = [0, 1].map((t) => { const b = sp0.filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
const pass = (arr, x, y) => x >= 0 && y >= 0 && x < W && y < H && arr[y * W + x] >= 0;
const dist = (arr, x, y) => { if (pass(arr, x, y)) return arr[y * W + x]; let b = 1e9; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (pass(arr, x + dx, y + dy)) b = Math.min(b, arr[(y + dy) * W + x + dx] + 1); return b >= 1e9 ? -1 : b; };
const f0 = (x, y) => { let a = geo ? dist(geo.dA, x, y) : -1, b = geo ? dist(geo.dB, x, y) : -1; if (a < 0 || b < 0) { a = Math.hypot(x - spc[0][0], y - spc[0][1]); b = Math.hypot(x - spc[1][0], y - spc[1][1]); } return a + b > 0 ? a / (a + b) : 0.5; };
const fT = (t, x, y) => (t === 0 ? f0(x, y) : 1 - f0(x, y));
const zn = (v) => (v < 0.4 ? 'own' : v <= 0.6 ? 'mid' : 'thr');
const atSpawn = (t, x, y) => cheb(x, y, spc[t][0], spc[t][1]) <= 2.6;
// camp groups
const camps = d.meta.camps;
const campAt = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
const par = new Map(camps.map((c) => [c.index, c.index]));
const find = (i) => { while (par.get(i) !== i) { par.set(i, par.get(par.get(i))); i = par.get(i); } return i; };
for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = campAt.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par.set(find(c.index), find(j)); }
const grp = new Map();
for (const c of camps) { const r = find(c.index); if (!grp.has(r)) grp.set(r, []); grp.get(r).push(c); }
const cls = (cs) => { const ty = cs.map((c) => String(c.type)); return ty.includes('monolith') ? 'MONO' : ty.includes('golem') || ty.includes('5') ? 'GOLEM' : ty.includes('elk') ? 'elk' : ty.includes('wolf') ? 'wolf' : 'clu'; };
const gOfTile = (x, y) => { const i = campAt.get(x * 1000 + y); if (i !== undefined) return find(i); let best = null, bd = 3; for (const [g, cs] of grp) for (const c of cs) { const dd = cheb(c.x, c.y, x, y); if (dd < bd) { bd = dd; best = g; } } return best; };
const S = new Array(final + 1);
for (let k = 1; k < d.R.length; k++) S[d.R[k][0]] = d.R[k];
for (let r = 1; r <= final; r++) if (!S[r]) S[r] = S[r - 1];
const ev = {};
for (const e of d.ev) (ev[e.k] ||= []).push(e);
const objCamp = new Set(camps.filter((c) => ['monolith', 'golem', '5', 5].includes(c.type)).map((c) => c.index));
console.log(`${name} ${W}x${H} team ${T} (${bodies.filter((b) => b.team === T).map((b) => short(b.type)).join(',')}) vs (${bodies.filter((b) => b.team !== T).map((b) => short(b.type)).join(',')}) -> ${d.meta.outcome === T + 1 ? 'WIN' : 'LOSS'} r${final} ${d.meta.submitted[T]}-${d.meta.submitted[1 - T]}`);
const objs = [...grp.entries()].filter(([, cs]) => ['MONO', 'GOLEM'].includes(cls(cs))).map(([g, cs]) => `${cls(cs)}@${cs[0].x},${cs[0].y}(f${fT(T, cs[0].x, cs[0].y).toFixed(2)})`);
if (objs.length) console.log(`  objectives: ${objs.join(' ')}`);
const clusters = (t, r) => {
  const live = S[r][3].filter((c) => teamOf(c[0]) === t && c[5]);
  const dead = S[r][3].filter((c) => teamOf(c[0]) === t && !c[5]).map((c) => short(bodies[c[0]].type));
  const seen = new Array(live.length).fill(false); const out = [];
  for (let i = 0; i < live.length; i++) {
    if (seen[i]) continue; const comp = []; const st = [i]; seen[i] = true;
    while (st.length) { const k = st.pop(); comp.push(live[k]); for (let j = 0; j < live.length; j++) if (!seen[j] && cheb(live[k][1], live[k][2], live[j][1], live[j][2]) <= 6) { seen[j] = true; st.push(j); } }
    const fm = comp.reduce((a, c) => a + fT(t, c[1], c[2]), 0) / comp.length;
    const home = comp.every((c) => atSpawn(t, c[1], c[2]));
    const bag = comp.reduce((a, c) => a + c[6], 0);
    const hp = comp.reduce((a, c) => a + c[3], 0) / comp.reduce((a, c) => a + c[4], 0);
    out.push(`[${comp.map((c) => short(bodies[c[0]].type) + (c[6] >= 30 ? ':' + c[6] : '')).join(' ')}]@${home ? 'HOME' : zn(fm) + fm.toFixed(2)}${hp < 0.6 ? ' hp' + Math.round(hp * 100) : ''}`);
  }
  return out.join(' ') + (dead.length ? ` dead(${dead.join(',')})` : '');
};
const win = (t, a, b) => {
  const parts = [];
  const caps = (ev.CaptureGems || []).filter((e) => e.team === t && e.r > a && e.r <= b);
  if (caps.length) {
    const byc = {};
    for (const e of caps) { const g = gOfTile(e.at[0], e.at[1]); const k = (g !== null ? cls(grp.get(g)) : '?') + '/' + zn(fT(t, e.at[0], e.at[1])); byc[k] = (byc[k] || 0) + e.gems; }
    parts.push(`cap ${caps.length}/${caps.reduce((s, e) => s + e.gems, 0)}g {${Object.entries(byc).map(([k, v]) => k + ':' + v).join(' ')}}`);
  }
  const banks = (ev.Banked || []).filter((e) => e.team === t && e.r > a && e.r <= b);
  if (banks.length) parts.push(`bank ${banks.length}/${banks.reduce((s, e) => s + e.gems, 0)}g${banks.filter((e) => e.gems >= 100).map((e) => ` BIG r${e.r} ${short(bodies[e.who].type)}${e.gems}@${zn(fT(t, e.at[0], e.at[1]))}`).join('')}`);
  const tribs = (ev['Submit gems'] || []).filter((e) => teamOf(e.who) === t && e.r > a && e.r <= b);
  const bigT = tribs.map((e) => { const c = S[Math.max(1, e.r - 1)][3].find((x) => x[0] === e.who); return [e, c ? c[6] : 0]; }).filter(([, g]) => g >= 100);
  if (bigT.length) parts.push(`tribute-start ${bigT.map(([e, g]) => `r${e.r} ${short(bodies[e.who].type)}${g}`).join(',')}`);
  const deaths = (ev.Death || []).filter((e) => teamOf(e.who) === t && e.r > a && e.r <= b);
  if (deaths.length) parts.push(`died ${deaths.map((e) => `r${e.r} ${short(bodies[e.who].type)}${e.bag ? ':' + e.bag : ''}@${zn(fT(t, e.at[0], e.at[1]))}${typeof e.by === 'number' ? '<' + short(bodies[e.by].type) : '<' + e.by}`).join(' ')}`);
  const kills = (ev.Death || []).filter((e) => teamOf(e.who) !== t && typeof e.by === 'number' && teamOf(e.by) === t && e.r > a && e.r <= b);
  if (kills.length) parts.push(`killed ${kills.map((e) => `r${e.r} ${short(bodies[e.who].type)}${e.bag ? ':' + e.bag : ''}`).join(' ')}`);
  let rec = 0;
  for (let r = a + 1; r <= b; r++) for (const c of S[r][3]) { if (teamOf(c[0]) !== t) continue; const p = S[r - 1]?.[3].find((x) => x[0] === c[0]); if (p && p[5] && c[5] && cheb(p[1], p[2], c[1], c[2]) > 2 && atSpawn(t, c[1], c[2]) && !atSpawn(t, p[1], p[2])) rec++; }
  if (rec) parts.push(`recall ${rec}`);
  const locks = (ev['Place altar lock'] || []).filter((e) => teamOf(e.who) === t && e.r > a && e.r <= b);
  if (locks.length) parts.push(`LOCK ${locks.map((e) => 'r' + e.r).join(',')}`);
  const od = d.cdmg.filter((x) => x[1] > a && x[1] <= b && teamOf(x[2]) === t && objCamp.has(x[3]));
  if (od.length) parts.push(`OBJ dmg ${od.reduce((s, x) => s + x[4], 0)} by ${new Set(od.map((x) => short(bodies[x[2]].type))).size} bodies`);
  const sh = (ev.Shop || []).filter((e) => teamOf(e.who) === t && e.r > a && e.r <= b).length;
  if (sh) parts.push(`shop ${sh}`);
  return parts.join('; ');
};
let a = 0;
while (a < final) {
  const K = a < 300 ? K1 : K2;
  const b = Math.min(final, a + K);
  const row = S[b];
  const mh = (t) => row[3].filter((c) => teamOf(c[0]) === t).reduce((s, c) => s + c[4], 0);
  console.log(`r${String(b).padStart(4)} ${String(row[1 + T]).padStart(4)}-${String(row[2 - T]).padEnd(4)} mhp ${mh(T)}-${mh(1 - T)} | ${clusters(T, b)} || ${clusters(1 - T, b)}`);
  const w1 = win(T, a, b), w2 = win(1 - T, a, b);
  if (w1) console.log(`        us: ${w1}`);
  if (w2) console.log(`        op: ${w2}`);
  a = b;
}
