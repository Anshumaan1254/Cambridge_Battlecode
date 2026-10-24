#!/usr/bin/env node
// Decision contexts per game and team from tools/live/fightdump.mjs dumps (playbook rules):
//   trib  every tribute start: [round, type, bag, own score, enemy score, done 0/1, allies within 8, enemies within 8 (alive, off their
//         spawn), altar zone (o/m/t by walking-distance share), own max-health sum / enemy max-health sum, carry share = bag / team carry]
//   obj   every monolith / golem kill effort that ended in a capture by anyone: [class, first hit round by the team, capture round, captured by
//         team (1) / enemy (0) / nobody (-1), team hitters, team bodies within 8 of the group at the capture, enemy bodies within 8,
//         team / enemy max-health sums at the first hit, score diff at the first hit]
//   lead  score diff and max-health diff at r100..r1000 step 100 (team minus enemy)
//   carry per 100 rounds: the team's largest bag and its holder type
// One JSON line per game: {file, t0: {...}, t1: {...}}.   node tools/top2/playbooks/pb_rules.mjs dump.json.gz...
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const GEO = new Map(fs.readFileSync('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => { const g = JSON.parse(l); return [g.map, g]; }));
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));

function one(file) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const name = path.basename(file).replace(/\.json\.gz$/, '');
  const g = GEO.get(name.replace(/_[0-9a-f]{8}$/, ''));
  const W = d.meta.width, H = d.meta.height, final = d.meta.finalRound;
  const bodies = d.meta.bodies;
  const teamOf = (i) => bodies[i].team;
  const sp0 = d.R[0][3];
  const spc = [0, 1].map((t) => { const b = sp0.filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
  const atSpawn = (t, x, y) => cheb(x, y, spc[t][0], spc[t][1]) <= 2.6;
  const pass = (arr, x, y) => x >= 0 && y >= 0 && x < W && y < H && arr[y * W + x] >= 0;
  const dist = (arr, x, y) => { if (pass(arr, x, y)) return arr[y * W + x]; let b = 1e9; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (pass(arr, x + dx, y + dy)) b = Math.min(b, arr[(y + dy) * W + x + dx] + 1); return b >= 1e9 ? -1 : b; };
  const f0 = (x, y) => { let a = g ? dist(g.dA, x, y) : -1, b = g ? dist(g.dB, x, y) : -1; if (a < 0 || b < 0) { a = Math.hypot(x - spc[0][0], y - spc[0][1]); b = Math.hypot(x - spc[1][0], y - spc[1][1]); } return a + b > 0 ? a / (a + b) : 0.5; };
  const zl = (t, x, y) => { const v = t === 0 ? f0(x, y) : 1 - f0(x, y); return v < 0.4 ? 'o' : v <= 0.6 ? 'm' : 't'; };
  const S = new Array(final + 1);
  for (let k = 1; k < d.R.length; k++) S[d.R[k][0]] = d.R[k];
  for (let r = 1; r <= final; r++) if (!S[r]) S[r] = S[r - 1];
  const at = (r) => S[Math.max(1, Math.min(final, r))];
  const mh = (r, t) => at(r)[3].filter((c) => teamOf(c[0]) === t).reduce((s, c) => s + c[4], 0);
  const banked = d.ev.filter((e) => e.k === 'Banked');
  const out = { file: name };
  // camp groups
  const camps = d.meta.camps;
  const campAt = new Map(camps.map((c) => [c.x * 1000 + c.y, c.index]));
  const par = new Map(camps.map((c) => [c.index, c.index]));
  const find = (i) => { while (par.get(i) !== i) { par.set(i, par.get(par.get(i))); i = par.get(i); } return i; };
  for (const c of camps) for (const [dx, dy] of [[1, 0], [0, 1]]) { const j = campAt.get((c.x + dx) * 1000 + c.y + dy); if (j !== undefined) par.set(find(c.index), find(j)); }
  const grp = new Map();
  for (const c of camps) { const r = find(c.index); if (!grp.has(r)) grp.set(r, []); grp.get(r).push(c); }
  const heavy = [...grp.entries()].map(([id, cs]) => ({ id, cs, cls: cs.some((c) => c.type === 'monolith') ? 'mono' : cs.some((c) => ['golem', 5, '5'].includes(c.type)) ? 'golem' : null })).filter((x) => x.cls);
  const caps = d.ev.filter((e) => e.k === 'CaptureGems');
  for (const t of [0, 1]) {
    const o = { trib: [], obj: [], lead: [], carry: [] };
    for (const e of d.ev.filter((x) => x.k === 'Submit gems' && teamOf(x.who) === t)) {
      const st = at(e.r - 1)[3];
      const me = st.find((c) => c[0] === e.who);
      const bag = me ? me[6] : 0;
      if (!me) continue;
      const done = banked.some((b) => b.who === e.who && b.r >= e.r && b.r <= e.r + Math.ceil(bag / 10) + 3) ? 1 : 0;
      const allies = st.filter((c) => teamOf(c[0]) === t && c[5] && cheb(c[1], c[2], me[1], me[2]) <= 8).length;
      const enem = st.filter((c) => teamOf(c[0]) !== t && c[5] && !atSpawn(1 - t, c[1], c[2]) && cheb(c[1], c[2], me[1], me[2]) <= 8).length;
      const carry = st.filter((c) => teamOf(c[0]) === t).reduce((s, c) => s + c[6], 0);
      const alt = e.to || [me[1], me[2]];
      o.trib.push([e.r, bodies[e.who].type, bag, at(e.r - 1)[1 + t], at(e.r - 1)[2 - t], done, allies, enem, zl(t, alt[0], alt[1]), +(mh(e.r, t) / Math.max(1, mh(e.r, 1 - t))).toFixed(2), +(bag / Math.max(1, carry)).toFixed(2)]);
    }
    for (const h of heavy) {
      const idx = new Set(h.cs.map((c) => c.index));
      const hits = d.cdmg.filter((x) => idx.has(x[3]));
      // efforts: split hits by gaps > 60 rounds
      let eff = [];
      for (const x of hits) { if (!eff.length || x[1] - eff[eff.length - 1].last > 60) eff.push({ first: x[1], last: x[1], hits: [] }); const E = eff[eff.length - 1]; E.last = x[1]; E.hits.push(x); }
      for (const E of eff) {
        const mine = E.hits.filter((x) => teamOf(x[2]) === t);
        if (!mine.length) continue;
        const cap = caps.find((c) => c.r >= E.first && c.r <= E.last + 40 && h.cs.some((cc) => cheb(cc.x, cc.y, c.at[0], c.at[1]) <= 2));
        const capBy = cap ? (cap.team === t ? 1 : 0) : -1;
        const r1 = mine[0][1];
        const rc = cap ? cap.r : E.last;
        const cx = h.cs[0].x, cy = h.cs[0].y;
        const near = (r, tt) => at(r)[3].filter((c) => teamOf(c[0]) === tt && c[5] && cheb(c[1], c[2], cx, cy) <= 8).length;
        o.obj.push([h.cls, r1, cap ? cap.r : null, capBy, new Set(mine.map((x) => x[2])).size, near(rc, t), near(rc, 1 - t), mh(r1, t), mh(r1, 1 - t), at(r1)[1 + t] - at(r1)[2 - t], zl(t, cx, cy), mine.reduce((s, x) => s + x[4], 0)]);
      }
    }
    for (let r = 100; r <= 1000; r += 100) {
      if (r > final) break;
      o.lead.push([r, at(r)[1 + t] - at(r)[2 - t], mh(r, t) - mh(r, 1 - t)]);
    }
    for (let r = 100; r <= final; r += 100) {
      const cs = at(r)[3].filter((c) => teamOf(c[0]) === t);
      const m = cs.reduce((a, c) => (c[6] > a[6] ? c : a), cs[0]);
      o.carry.push([r, m[6], bodies[m[0]].type, cs.reduce((s, c) => s + c[6], 0)]);
    }
    out['t' + t] = o;
  }
  return out;
}
for (const f of process.argv.slice(2)) {
  try { console.log(JSON.stringify(one(f))); } catch (e) { console.log(JSON.stringify({ file: path.basename(f), err: String(e.stack || e) })); }
}
