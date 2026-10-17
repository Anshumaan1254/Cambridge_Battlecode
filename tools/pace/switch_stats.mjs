import fs from 'fs';
import { unwrapReplay } from '../replay/decode.mjs';
const files = process.argv.slice(2);
const st = {};
const add = (k, v) => { st[k] = st[k] || { n: 0, steps: 0 }; st[k].n++; st[k].steps += v; };
for (const f of files) {
  const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const t = unwrapReplay(fs.readFileSync(f), our ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  for (const l of t.split('\n')) {
    const m = l.trim().match(/^SW r=(\d+) (\d+) old=(\d+) new=(\d+) sold=(-?[\d.]+) snew=(-?[\d.]+) stold=(\d) dold=(\d+) dnew=(\d+) since=(\d+)/);
    if (!m) continue;
    const r = +m[1], sold = +m[5], stold = +m[7], dold = +m[8], dnew = +m[9], since = +m[10];
    if (since < 3) { add('quick(<3 rounds)', since); continue; }
    let k;
    if (sold < 0) k = 'old invalid st=' + stold; else k = 'old valid (rescore)';
    add(k + (dnew < dold ? ' new nearer' : ' new farther'), since);
  }
}
for (const [k, v] of Object.entries(st).sort()) console.log(k.padEnd(40), v.n, 'switches', v.steps, 'rounds walked');
