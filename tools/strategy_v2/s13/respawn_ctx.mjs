// own-side camps of our team: at each respawn, nearest alive ally distance, alive count, delay to first touch
import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const acc = { n: 0, delay: 0, near5: 0, dead: 0, far: 0, nearIdle: 0, buckets: {} };
const accT = { n: 0, delay: 0, near5: 0, far: 0 };
for (const [file, usSide] of process.argv.slice(2).map(a => a.split(':'))) {
  const d = await decode(fs.readFileSync(file));
  for (const team of [0, 1]) {
    const us = team, A = team === (usSide === 'A' ? 0 : 1) ? acc : accT;
    const r1 = d.rounds[1].ch;
    const sp = [0, 1].map(t => { const c = r1.filter(c => c[1] === t); return [c.reduce((s, x) => s + x[3], 0) / c.length, c.reduce((s, x) => s + x[4], 0) / c.length]; });
    const own = p => { const da = Math.hypot(p[0] - sp[us][0], p[1] - sp[us][1]), de = Math.hypot(p[0] - sp[1 - us][0], p[1] - sp[1 - us][1]); return da < de && Math.abs(da - de) >= 0.12 * (da + de); };
    const camps = d.meta.camps, R = d.rounds;
    for (let i = 0; i < camps.length; i++) {
      if (!own([camps[i].x, camps[i].y])) continue;
      const mx = camps[i].hp; let dead = false, resp = -1;
      for (let k = 1; k < R.length; k++) {
        const h = R[k].campHp?.[i]; if (h === undefined) break;
        if (h <= 0) { dead = true; resp = -1; continue; }
        if (dead && h >= mx) {
          dead = false; resp = k;
          const al = R[k].ch.filter(c => c[1] === us && c[7]);
          const nd = Math.min(99, ...al.map(c => Math.max(Math.abs(c[3] - camps[i].x), Math.abs(c[4] - camps[i].y))));
          A._nd = nd; A._dead = R[k].ch.filter(c => c[1] === us && !c[7]).length;
          continue;
        }
        if (resp > 0 && h < mx) {
          const dl = k - resp; A.n++; A.delay += dl; if (A._nd <= 5) A.near5++; else A.far = (A.far ?? 0) + 1;
          const b = dl <= 5 ? '0-5' : dl <= 15 ? '6-15' : dl <= 40 ? '16-40' : '41+';
          if (A.buckets) A.buckets[b] = (A.buckets[b] ?? 0) + 1;
          if (A.dead !== undefined) A.dead += A._dead;
          resp = -1;
        }
      }
    }
  }
}
const f = A => `respawns ${A.n} mean delay ${(A.delay / A.n).toFixed(1)} ally<=5 at respawn ${(100 * A.near5 / A.n).toFixed(0)}% ${A.buckets ? JSON.stringify(A.buckets) : ''} ${A.dead !== undefined ? 'dead bodies avg ' + (A.dead / A.n).toFixed(2) : ''}`;
console.log('US  ', f(acc)); console.log('THEM', f(accT));
