// usage: node tools/econ/waste.mjs FILE.repl26a...   (agent econ; needs LEGEND_TRACE builds: G and T lines; our bot = team A unless *_B.repl26a)
// Body time on camp targets that produced nothing: a segment = consecutive turns with the same (task, group) for farm/capture/wait.
// A segment is "wasted" when the body neither attacked a camp of that group nor captured it during the segment.
// Prints per game and in total: share of alive body-rounds in wasted segments, split by the state the group had when the
// segment started (as far as the trace shows: wait task = respawn, capt = reward) and by champion.
import fs from 'node:fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';
const files = process.argv.slice(2);
const TOT = { alive: 0, waste: 0, byTask: {}, byChamp: {}, segs: 0, wsegs: 0 };
for (const f of files) {
  const B = /_B\.repl26a$/.test(f) ? 1 : 0;
  const buf = fs.readFileSync(f);
  const t = unwrapReplay(buf, B ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const d = await decode(buf);
  const tiles = new Map(); // "x,y" -> gid
  for (const l of t.split('\n')) {
    const m = l.trim().match(/^G id=(\d+) .* tiles=(.*)$/);
    if (m) for (const p of m[2].split(';').filter(Boolean)) tiles.set(p, +m[1]);
  }
  // our bodies: champion index -> type; T lines carry type, not index: map type -> index
  const typeIdx = new Map();
  for (const b of d.meta.bodies) if (b.team === B) typeIdx.set(CHAMP.indexOf(b.type), b.index);
  const hits = new Set(); // "who:gid:r"
  for (const e of d.events) {
    if (e.team !== B) continue;
    if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) { const g = tiles.get(e.to[0] + ',' + e.to[1]); if (g !== undefined) hits.add(`${e.who}:${g}:${e.r}`); }
    if (e.k === 'CaptureGems') { const g = tiles.get(e.at[0] + ',' + e.at[1]); hits.add(`${e.who}:${g ?? 'any'}:${e.r}`); hits.add(`${e.who}:cap:${e.r}`); }
  }
  const names = ['none', 'farm', 'capt', 'wait', 'trib', 'home', 'fight', 'flee'];
  const segs = new Map(); // type -> current seg
  const G = { alive: 0, waste: 0, byTask: {}, byChamp: {}, segs: 0, wsegs: 0 };
  const close = (ty, s) => {
    if (!s) return;
    const who = typeIdx.get(ty);
    let prod = false;
    for (let r = s.r0; r <= s.r1 + 8 && !prod; ++r) prod = (r <= s.r1 + 1 && hits.has(`${who}:${s.g}:${r}`)) || hits.has(`${who}:cap:${r}`);
    const n = s.r1 - s.r0 + 1;
    G.segs++;
    if (!prod) { G.waste += n; G.wsegs++; G.byTask[names[s.task]] = (G.byTask[names[s.task]] || 0) + n; G.byChamp[CHAMP[ty]] = (G.byChamp[CHAMP[ty]] || 0) + n; }
  };
  for (const l of t.split('\n')) {
    const m = l.trim().match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+)/);
    if (!m) continue;
    const r = +m[1], ty = +m[2], task = +m[3], g = +m[4];
    G.alive++;
    const cur = segs.get(ty);
    const camp = (task === 1 || task === 2 || task === 3) && g >= 0;
    if (cur && camp && cur.g === g && r <= cur.r1 + 2) { cur.r1 = r; if (task !== cur.task && task === 1) cur.task = 1; continue; }
    close(ty, cur);
    segs.set(ty, camp ? { r0: r, r1: r, g, task } : null);
  }
  for (const [ty, s] of segs) close(ty, s);
  const fmt = (o, n) => Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${(100 * v / n).toFixed(1)}`).join(', ');
  console.log(`${f.split('/').pop().padEnd(28)} wasted ${(100 * G.waste / G.alive).toFixed(1)}% of ${G.alive} body-rounds (${G.wsegs}/${G.segs} segments)  by task: ${fmt(G.byTask, G.alive)}  by champ: ${fmt(G.byChamp, G.alive)}`);
  TOT.alive += G.alive; TOT.waste += G.waste; TOT.segs += G.segs; TOT.wsegs += G.wsegs;
  for (const k in G.byTask) TOT.byTask[k] = (TOT.byTask[k] || 0) + G.byTask[k];
  for (const k in G.byChamp) TOT.byChamp[k] = (TOT.byChamp[k] || 0) + G.byChamp[k];
}
if (files.length > 1) {
  const fmt = (o, n) => Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${(100 * v / n).toFixed(1)}`).join(', ');
  console.log(`TOTAL wasted ${(100 * TOT.waste / TOT.alive).toFixed(1)}% (${TOT.wsegs}/${TOT.segs} segments)  by task: ${fmt(TOT.byTask, TOT.alive)}  by champ: ${fmt(TOT.byChamp, TOT.alive)}`);
}
