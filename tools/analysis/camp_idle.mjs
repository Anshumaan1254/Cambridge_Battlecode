// usage: node tools/analysis/camp_idle.mjs REPLAY...   (bench naming *_A / *_B: our team)
// Unused supply: for every gem-bearing camp (wolf, elk, gem cluster, monolith) on our half (nearer our spawn), the share of
// the game it stood alive at full health (respawned, nobody hitting it). High values = camps waiting for a farmer while
// bodies walk elsewhere. Per camp type, mean over camps; plus the share of rounds with at least one such camp per type.
import fs from 'fs';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const files = process.argv.slice(2);
const agg = {};
for (const f of files) {
  const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const d = await decode(unwrapReplay(fs.readFileSync(f)), { every: 1 });
  const camps = d.meta.camps;
  // our half: champion start positions of our team = spawn; nearer by Chebyshev to our first body's r1 position
  const r0 = d.rounds[0];
  const me = r0.ch.find((c) => c[1] === our), op = r0.ch.find((c) => c[1] !== our);
  const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
  const out = [];
  for (let i = 0; i < camps.length; i++) {
    const c = camps[i];
    if (c.type === 'gold') continue;
    if (cheb([c.x, c.y], [me[3], me[4]]) > cheb([c.x, c.y], [op[3], op[4]])) continue;
    let full = 0;
    for (const r of d.rounds) if (r.campHp[i] >= c.hp && c.hp > 0) full++;
    out.push([c.type, full / d.rounds.length]);
    const a = (agg[c.type] ||= { n: 0, s: 0 }); a.n++; a.s += full / d.rounds.length;
  }
  const by = {};
  for (const [t, v] of out) (by[t] ||= []).push(v);
  console.log(f.split('/').pop().padEnd(26), `r${d.meta.finalRound}`, Object.entries(by).map(([t, v]) => `${t} ${v.length}x ${(100 * v.reduce((a, b) => a + b, 0) / v.length).toFixed(0)}%`).join('  '));
}
console.log('mean', Object.entries(agg).map(([t, a]) => `${t} ${(100 * a.s / a.n).toFixed(0)}% (${a.n})`).join('  '));
