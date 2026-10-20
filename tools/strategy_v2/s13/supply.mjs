import fs from 'node:fs';
import { unwrapReplay } from '../../replay/decode.mjs';
for (const f of process.argv.slice(2)) {
  const t = unwrapReplay(fs.readFileSync(f), 'team-a.stdout').toString('latin1');
  let rate = 0, rateAll = 0, n = 0, gold = 0;
  for (let l of t.split('\n')) {
    l = l.replace(/\x00/g, '').trim();
    const m = l.match(/^G id=(\d+) gems=(\d+) gold=(\d+) respawn=(\d+) ours=(\d) d_ally=(\d+) hp=(\d+)/);
    if (!m) continue;
    const gems = +m[2], resp = +m[4], hp = +m[7], ours = +m[5];
    if (hp >= 20000) continue;
    const r = gems / (resp + 6 + hp / 120);
    rateAll += r; if (ours) { rate += r; n++; gold += +m[3] / (resp + 6 + hp / 120); }
  }
  console.log(f.split('/').pop().padEnd(28), 'own groups', n, 'gem rate', rate.toFixed(2), '-> 1000 in', Math.round(1000 / rate), ' all-map rate', rateAll.toFixed(2), Math.round(1000 / rateAll));
}
