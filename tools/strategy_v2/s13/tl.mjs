// tl.mjs REPLAY [team]: per body: target group timeline (compressed) from LEGEND_TRACE T lines
import fs from 'node:fs';
import { unwrapReplay } from '../../replay/decode.mjs';
const f = process.argv[2], team = process.argv[3] || (/_B\.repl26a$/.test(f) ? 'b' : 'a');
const t = unwrapReplay(fs.readFileSync(f), `team-${team}.stdout`).toString('latin1');
const TN = ['Ryth','Vesper','Vend','Cassi','Issac','Stellar','Prism','Marc','Willow','Ren','Varg','Tavi'];
const TK = ['none','farm','cap','wait','trib','home','fight','flee'];
const seq = {};
for (let l of t.split('\n')) {
  l = l.replace(/\x00/g, '').trim();
  const m = l.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\) hp=(\d+) gems=(\d+)/);
  if (!m) continue;
  const b = TN[+m[2]]; (seq[b] ||= []).push([+m[1], TK[+m[3]], +m[4], +m[8]]);
}
const maxr = +(process.argv[4] || 9999);
for (const [b, s] of Object.entries(seq)) {
  let out = [], cur = null, start = 0;
  for (const [r, tk, g, gems] of s) {
    if (r > maxr) break;
    const key = tk + (['farm','cap','wait'].includes(tk) ? g : '');
    if (key !== cur) { if (cur !== null) out.push(`${start}:${cur}`); cur = key; start = r; }
  }
  out.push(`${start}:${cur}`);
  console.log(b.padEnd(8), out.join(' '));
}
