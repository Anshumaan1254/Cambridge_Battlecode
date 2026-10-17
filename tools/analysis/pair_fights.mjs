#!/usr/bin/env node
// Outcome of fight starts by champion (agent `pair`, session 5). Needs XM_TRACE builds (FC / FX lines from combat()).
//
//   node tools/analysis/pair_fights.mjs [--all] DIR...
//
// A fight start = an FC line with fight=1 whose body had no fight=1 line the round before. Only escapable starts
// (esc=1) are counted unless --all. Outcome over the next 12 rounds: did this body die (for Cassi / Issac: the pair),
// how many enemy bodies died within 8 tiles of the start. Bins by health, advantage, visible enemies, remembered
// (hidden, recently seen) enemies, and the body's own survival ratio (own health / enemy dps) / (time to kill them).
// Value per start = kills x 1 body - deaths x bodies lost (2 for the pair).
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const ALL = args.includes('--all');
const dirs = args.filter((a) => !a.startsWith('--'));
const files = [];
for (const d of dirs) {
  const walk = (p) => {
    if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f));
    else if (p.endsWith('.repl26a')) files.push(p);
  };
  walk(d);
}
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const NAMES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
const B = {};
const add = (grp, key, died, kills, cost) => {
  const o = ((B[grp] ||= {})[key] ||= { n: 0, d: 0, k: 0, net: 0 });
  o.n++; o.d += died; o.k += kills; o.net += kills - died * cost;
};
for (const f of files.sort()) {
  const base = path.basename(f, '.repl26a');
  const us = base.slice(-1) === 'A' ? 0 : 1;
  const raw = fs.readFileSync(f);
  let text;
  try { text = unwrapReplay(raw, us ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, ''); } catch { continue; }
  const fc = new Map(), fx = new Map();
  for (const l of text.split('\n')) {
    if (!l.startsWith('FC ') && !l.startsWith('FX ')) continue;
    const kv = Object.fromEntries(l.slice(3).trim().split(' ').map((t) => t.split('=')));
    (l[1] === 'C' ? fc : fx).set(`${kv.ty}:${kv.r}`, kv);
  }
  const d = await decode(unwrapReplay(raw));
  const deaths = d.events.filter((e) => e.k === 'Death');
  const bodyOf = new Map(d.meta.bodies.filter((b) => b.team === us).map((b) => [NAMES.indexOf(b.type), b.index]));
  for (const [k, x] of fc) {
    if (x.fight !== '1' || (!ALL && x.esc !== '1')) continue;
    const ty = +x.ty, r = +x.r;
    const p = fc.get(`${ty}:${r - 1}`);
    if (p && p.fight === '1') continue;
    const idx = bodyOf.get(ty);
    if (idx === undefined) continue;
    const at = [+x.x, +x.y];
    const died = deaths.some((e) => e.team === us && e.who === idx && e.r > r && e.r <= r + 12) ? 1 : 0;
    const kills = deaths.filter((e) => e.team !== us && e.r > r && e.r <= r + 12 && cheb(e.at, at) <= 8).length;
    const pair = ty === 3 || ty === 4;
    const cost = pair ? 2 : 1;
    const grp = pair ? 'C&I' : 'other';
    const hpf = +x.hp / Math.max(1, +x.mhp);
    const X = fx.get(k) || { mn: 0 };
    const surv = (+x.hp / Math.max(1, +x.tdps)) / Math.max(0.1, +x.tkt); // own health vs all their dps, over the time to kill them
    add(grp, 'all', died, kills, cost);
    add(grp + ' hp', hpf < 0.4 ? '<40' : hpf < 0.6 ? '40-60' : hpf < 0.8 ? '60-80' : '80+', died, kills, cost);
    add(grp + ' adv', +x.adv < 1.5 ? '<1.5' : +x.adv < 2 ? '1.5-2' : +x.adv < 3 ? '2-3' : '3+', died, kills, cost);
    add(grp + ' ne', x.ne, died, kills, cost);
    add(grp + ' mem', String(Math.min(2, +X.mn)), died, kills, cost);
    add(grp + ' surv', surv < 0.5 ? '<0.5' : surv < 1 ? '0.5-1' : surv < 2 ? '1-2' : '2+', died, kills, cost);
    add(grp + ' rule', x.kill === '1' ? 'kill' : +x.adv >= +x.fm ? 'margin' : x.reach === '1' ? 'back' : 'other', died, kills, cost);
    add(grp + ' na', x.na, died, kills, cost);
    add(grp + ' iso', x.iso, died, kills, cost);
  }
}
for (const [g, o] of Object.entries(B).sort()) {
  console.log(g);
  for (const [k, v] of Object.entries(o).sort())
    console.log(`   ${k.padEnd(7)} n ${String(v.n).padStart(5)}  death ${(100 * v.d / v.n).toFixed(1).padStart(5)}%  kills/start ${(v.k / v.n).toFixed(2)}  net/start ${(v.net / v.n).toFixed(2)}`);
}
