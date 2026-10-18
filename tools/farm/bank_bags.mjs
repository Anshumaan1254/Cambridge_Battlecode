// usage: node tools/farm/bank_bags.mjs FILE.repl26a... : per team, number of banks, mean bag, and mean Chebyshev distance of the bank from the team's spawn
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const tot = [{ n: 0, g: 0, d: 0 }, { n: 0, g: 0, d: 0 }];
for (const f of process.argv.slice(2)) {
  const d = await decode(fs.readFileSync(f));
  const sp = [null, null];
  const r0 = d.rounds.find((s) => s.ch.length);
  for (const t of [0, 1]) { const c = r0.ch.filter((c) => c[1] === t); sp[t] = [c.reduce((a, c) => a + c[3], 0) / c.length, c.reduce((a, c) => a + c[4], 0) / c.length]; }
  const per = [{ n: 0, g: 0, d: 0 }, { n: 0, g: 0, d: 0 }];
  for (const e of d.events) if (e.k === 'Banked') { const t = e.team, p = per[t]; p.n++; p.g += e.gems; p.d += Math.max(Math.abs(e.at[0] - sp[t][0]), Math.abs(e.at[1] - sp[t][1])); }
  const s = (p) => `${p.n} banks, bag ${(p.g / Math.max(1, p.n)).toFixed(0)}, ${(p.d / Math.max(1, p.n)).toFixed(0)} from spawn`;
  console.log(f.split('/').pop().padEnd(22), 'A:', s(per[0]).padEnd(36), 'B:', s(per[1]));
  for (const t of [0, 1]) { tot[t].n += per[t].n; tot[t].g += per[t].g; tot[t].d += per[t].d; }
}
console.log('ALL'.padEnd(22), 'A:', `${tot[0].n} banks, bag ${(tot[0].g / tot[0].n).toFixed(0)}`, ' B:', `${tot[1].n} banks, bag ${(tot[1].g / tot[1].n).toFixed(0)}`);
