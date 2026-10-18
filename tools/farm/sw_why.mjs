// usage: node tools/farm/sw_why.mjs FILE.repl26a... : target switches (LEGEND_TRACE SW lines with why=) by cause, rounds walked toward the old target
import fs from 'node:fs';
import { unwrapReplay } from '../replay/decode.mjs';
const WHY = { 0: 'valid (rescored lower)', 1: 'monolith off', 2: 'obj open', 3: 'unreachable', 4: 'reward: lower claimer nearer', 5: 'respawn too far off',
  6: 'join not allowed (claimed)', 7: 'cannot clear solo', 8: 'cannot clear with pair', 9: 'steal hp', 10: 'threat', 11: 'blacklisted', 12: 'no_split: ally on reward', 13: 'join_reach: claimers done first' };
const st = {}, per = {};
const add = (k, v) => { st[k] = st[k] || { n: 0, r: 0 }; st[k].n++; st[k].r += v; };
for (const f of process.argv.slice(2)) {
  const t = unwrapReplay(fs.readFileSync(f), /_B\.repl26a$/.test(f) ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const map = f.split('/').pop().replace(/_[AB]\.repl26a$/, '');
  for (const l of t.split('\n')) {
    const m = l.trim().match(/^SW r=(\d+) (\d+) old=(\d+) new=(-?\d+) sold=(-?[\d.]+) snew=(-?[\d.]+) stold=(\d) dold=(\d+) dnew=(\d+) since=(\d+) why=(\d+)/);
    if (!m) continue;
    const since = +m[10], stold = +m[7], why = +m[11], sold = +m[5];
    const k = (sold > 0 ? WHY[0] : (WHY[why] || why)) + ' st=' + stold;
    add(k, since);
    per[map] = per[map] || {}; per[map][k] = (per[map][k] || 0) + since;
  }
}
for (const [k, v] of Object.entries(st).sort((a, b) => b[1].r - a[1].r)) console.log(k.padEnd(45), String(v.n).padStart(5), 'switches', String(v.r).padStart(6), 'rounds since target set');
if (process.argv.includes('--maps')) for (const [m, o] of Object.entries(per)) console.log(m, JSON.stringify(o));
