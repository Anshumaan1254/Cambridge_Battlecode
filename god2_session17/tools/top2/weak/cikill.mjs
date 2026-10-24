#!/usr/bin/env node
// Cassi & Issac deaths (an_weak): which of the pair was hit by the killing action (the Attack / Cast / camp step whose target tile holds
// the body, or the body with the lower hp just before), hp of both before the step, distance between the pair, killer type.
//   node tools/top2/weak/cikill.mjs dump.json.gz...  -> one JSON line per C&I death pair
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
for (const file of process.argv.slice(2)) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
  const ty = (i) => d.meta.bodies[i]?.type;
  const PM = new Map(); for (const e of d.R) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(e[0], m); }
  const deaths = d.ev.filter((e) => e.k === 'Death' && (ty(e.who) === 'Cassi' || ty(e.who) === 'Issac'));
  const seen = new Set();
  for (const e of deaths) {
    if (seen.has(e.q)) continue; seen.add(e.q);
    const pair = deaths.filter((x) => x.q === e.q).map((x) => x.who);
    if (pair.length < 2) continue;
    const act = d.ev.find((x) => x.q === e.q && x.k !== 'Death' && x.to);
    const prev = PM.get(e.r - 1) || PM.get(e.r);
    const st = pair.map((b) => { const c = prev.get(b); return { b, ty: ty(b), x: c?.[1], y: c?.[2], hp: c?.[3], mh: c?.[4] }; });
    // the pair positions at the death step = the 'at' of the Death events
    const at = new Map(deaths.filter((x) => x.q === e.q).map((x) => [x.who, x.at]));
    let hit = null;
    if (act) for (const b of pair) { const p = at.get(b); if (p && cheb(p[0], p[1], act.to[0], act.to[1]) <= (act.k === 'Cast ability' ? 1 : 0)) { hit = ty(b); if (cheb(p[0], p[1], act.to[0], act.to[1]) === 0) break; } }
    if (!hit && e.by === 'camp') { const lo = st.reduce((a, s) => (s.hp / s.mh < a.hp / a.mh ? s : a)); hit = lo.ty + '?'; }
    const pa = at.get(pair[0]), pb = at.get(pair[1]);
    console.log(JSON.stringify({ file: path.basename(file), r: e.r, team: e.team, hit, by: typeof e.by === 'number' ? ty(e.by) : e.by, sep: pa && pb ? cheb(pa[0], pa[1], pb[0], pb[1]) : null, st: st.map((s) => `${s.ty} ${s.hp}/${s.mh}`) }));
  }
}
