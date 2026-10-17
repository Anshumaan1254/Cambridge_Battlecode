// Per-round damage taken vs prediction, split by kit, ally presence and live camps.
// usage: node tools/analysis/xm_fr_split.mjs DIR [DIR...]
import fs from 'fs'; import path from 'path';
import { unwrapReplay } from '../replay/decode.mjs';
const T = ['Ryth','Vesper','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi'];
const P = l => Object.fromEntries(l.trim().split(/\s+/).slice(1).map(x=>x.split('=')).map(([k,v])=>[k,isNaN(+v)?v:+v]));
const rows = [];
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir).filter(f=>f.endsWith('.repl26a'))) {
  const side = f.endsWith('_A.repl26a') ? 'team-a.stdout' : 'team-b.stdout';
  let t; try { t = unwrapReplay(fs.readFileSync(path.join(dir,f)), side).toString('latin1').replace(/\0/g,''); } catch { continue; }
  for (const l of t.split('\n')) if (l.startsWith('FR ')) rows.push(P(l));
}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0);
const cl = rows.filter(o => o.clean && !o.killed && o.share >= 0 && o.pin > 0);
console.log('clean rows', cl.length);
for (const ty of [3,5]) for (const vis of [0,1]) for (const live of [1,2,3,4]) {
  const s = cl.filter(o => o.ty === ty && o.claim === 0 && (o.vis > 0) === !!vis && Math.min(4, o.live) === live);
  if (s.length < 30) continue;
  const zero = s.filter(o => o.lost === 0).length;
  console.log(`${T[ty].padEnd(8)} solo-claim vis=${vis} live=${live} n=${String(s.length).padStart(5)} actual/in ${(sum(s,o=>o.lost)/sum(s,o=>o.pin)).toFixed(2)} actual/near ${(sum(s,o=>o.lost)/Math.max(1,sum(s,o=>o.near))).toFixed(2)} near/in ${(sum(s,o=>o.near)/sum(s,o=>o.pin)).toFixed(2)} zero-dmg rounds ${(100*zero/s.length).toFixed(0)}%`);
}
for (const ty of [0,4,9,10]) for (const vis of [0,1]) {
  const s = cl.filter(o => o.ty === ty && o.claim === 0 && (o.vis > 0) === !!vis);
  if (s.length < 30) continue;
  const zero = s.filter(o => o.lost === 0).length;
  console.log(`${T[ty].padEnd(8)} solo-claim vis=${vis} n=${String(s.length).padStart(5)} actual/in ${(sum(s,o=>o.lost)/sum(s,o=>o.pin)).toFixed(2)} zero-dmg rounds ${(100*zero/s.length).toFixed(0)}%`);
}
// new-model rows (if present): share (new) vs share0 (old)
const nw = cl.filter(o => o.share0 !== undefined && o.share0 >= 0);
if (nw.length) {
  console.log(`\nnew trace rows ${nw.length}`);
  for (const ty of [0,3,4,5,9,10]) {
    const s = nw.filter(o => o.ty === ty);
    if (s.length < 30) continue;
    const mae = f => sum(s, o => Math.abs(f(o) - o.lost)) / s.length;
    console.log(`${T[ty].padEnd(8)} n=${String(s.length).padStart(5)} actual/old ${(sum(s,o=>o.lost)/sum(s,o=>o.pin*o.share0)).toFixed(2)} MAE ${mae(o=>o.pin*o.share0).toFixed(1)} | actual/new ${(sum(s,o=>o.lost)/sum(s,o=>o.pin*o.share)).toFixed(2)} MAE ${mae(o=>o.pin*o.share).toFixed(1)}`);
  }
  const mae = f => sum(nw, o => Math.abs(f(o) - o.lost)) / nw.length, bias = f => sum(nw, o => f(o) - o.lost) / nw.length;
  console.log(`all: old MAE ${mae(o=>o.pin*o.share0).toFixed(2)} bias ${bias(o=>o.pin*o.share0).toFixed(2)} | new MAE ${mae(o=>o.pin*o.share).toFixed(2)} bias ${bias(o=>o.pin*o.share).toFixed(2)} | mean actual ${(sum(nw,o=>o.lost)/nw.length).toFixed(2)}`);
}
