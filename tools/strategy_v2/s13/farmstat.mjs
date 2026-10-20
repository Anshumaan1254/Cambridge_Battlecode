// per game: capture grouping (allies within 3 at capture), respawn -> first touch delay per side, captures per side
import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const out = [];
for (const [file, usSide] of process.argv.slice(2).map(a => a.split(':'))) {
  const d = await decode(fs.readFileSync(file));
  const us = usSide === 'A' ? 0 : 1;
  const r1 = d.rounds[1].ch;
  const sp = [0, 1].map(t => { const c = r1.filter(c => c[1] === t); return [c.reduce((s, x) => s + x[3], 0) / c.length, c.reduce((s, x) => s + x[4], 0) / c.length]; });
  const sideOf = (t, p) => { const da = Math.hypot(p[0] - sp[t][0], p[1] - sp[t][1]), de = Math.hypot(p[0] - sp[1 - t][0], p[1] - sp[1 - t][1]); return Math.abs(da - de) < 0.12 * (da + de) ? 'neu' : da < de ? 'own' : 'opp'; };
  const S = { 0: { cap: 0, gems: 0, grp: 0, soloGems: 0 }, 1: { cap: 0, gems: 0, grp: 0, soloGems: 0 } };
  for (const e of d.events) if (e.k === 'CaptureGems') {
    const t = d.meta.bodies[e.who].team; const r = d.rounds[e.r];
    const me = r.ch.find(c => c[0] === e.who);
    const n = r.ch.filter(c => c[1] === t && c[7] && c[0] !== e.who && me && Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4])) <= 3).length;
    S[t].cap++; S[t].gems += e.gems; if (n > 0) S[t].grp++; else S[t].soloGems += e.gems;
  }
  // respawn -> first touch
  const camps = d.meta.camps; const R = d.rounds;
  const delay = { own: [], neu: [], opp: [] }; // from OUR perspective
  for (let i = 0; i < camps.length; i++) {
    const mx = camps[i].hp; let dead = false, resp = -1;
    for (let k = 1; k < R.length; k++) {
      const h = R[k].campHp?.[i]; if (h === undefined) break;
      if (h <= 0) { dead = true; resp = -1; continue; }
      if (dead && h >= mx) { dead = false; resp = k; continue; }
      if (resp > 0 && h < mx) { delay[sideOf(us, [camps[i].x, camps[i].y])].push(k - resp); resp = -1; }
    }
  }
  const avg = a => a.length ? (a.reduce((s, x) => s + x, 0) / a.length).toFixed(1) + '(' + a.length + ')' : '-';
  console.log(file.split('/').pop(), d.meta.drafts[1 - us].join(','), 'us cap', S[us].cap, 'grp', S[us].grp, 'gems', S[us].gems, 'solo', S[us].soloGems, '| them cap', S[1 - us].cap, 'grp', S[1 - us].grp, 'gems', S[1 - us].gems, 'solo', S[1 - us].soloGems, '| touch delay ourside', avg(delay.own), 'neutral', avg(delay.neu), 'theirside', avg(delay.opp));
}
