// usage: node tools/farm/task_share.mjs FILE.repl26a... : share of our alive turns per task (LEGEND_TRACE T lines), wait split by target / none
import fs from 'node:fs';
import { unwrapReplay } from '../replay/decode.mjs';
const names = ['none', 'farm', 'capt', 'wait', 'trib', 'home', 'fight', 'flee'];
const tot = {};
for (const f of process.argv.slice(2)) {
  const t = unwrapReplay(fs.readFileSync(f), /_B\.repl26a$/.test(f) ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const c = {}; let n = 0;
  for (const l of t.split('\n')) {
    const m = l.trim().match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+)/);
    if (!m) continue;
    let k = names[+m[3]]; if (k === 'wait') k += +m[4] < 0 ? '(none)' : '(group)';
    c[k] = (c[k] || 0) + 1; n++; tot[k] = (tot[k] || 0) + 1; tot.n = (tot.n || 0) + 1;
  }
  console.log(f.split('/').pop().padEnd(22), Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}=${(100 * v / n).toFixed(1)}`).join(' '));
}
const n = tot.n; delete tot.n;
console.log('ALL'.padEnd(22), Object.entries(tot).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}=${(100 * v / n).toFixed(1)}`).join(' '));
