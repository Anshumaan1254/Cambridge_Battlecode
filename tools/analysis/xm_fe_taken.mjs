// Episode damage taken vs the plan's prediction, by number of attacking camps (GI join), and the sequential-kill
// integral model: camps killed one by one stop attacking, so the mean incoming over the kill is (n+1)/(2n) of
// the initial incoming for n equal camps.
// usage: node tools/analysis/xm_fe_taken.mjs DIR [DIR...]
import fs from 'fs'; import path from 'path';
import { unwrapReplay } from '../replay/decode.mjs';
const T = ['Ryth','Vesper','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi'];
const P = l => Object.fromEntries(l.trim().split(/\s+/).slice(1).map(x=>x.split('=')).map(([k,v])=>[k,isNaN(+v)?v:+v]));
const FE = [];
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir).filter(f=>f.endsWith('.repl26a'))) {
  const side = f.endsWith('_A.repl26a') ? 'team-a.stdout' : 'team-b.stdout';
  let t; try { t = unwrapReplay(fs.readFileSync(path.join(dir,f)), side).toString('latin1').replace(/\0/g,''); } catch { continue; }
  const gi = {};
  const lines = t.split('\n');
  for (const l of lines) if (l.startsWith('GI ')) { const o = P(l); gi[o.g] = o; }
  for (const l of lines) if (l.startsWith('FE ')) { const o = P(l); o.gi = gi[o.g]; o.game = f; FE.push(o); }
}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0), mean=(a,f)=>a.length?sum(a,f)/a.length:NaN;
const kills = FE.filter(o => o.why === 'kill' && o.plan === 1 && o.eng >= 0 && o.pin > 0 && o.gi);
const att = o => o.gi.wolf + o.gi.elk + o.gi.mono;
console.log('attackers  kit     n   pred taken  act lost  ratio | seq (n+1)/2n ratio');
for (const ranged of [0, 1]) for (let n = 1; n <= 4; ++n) {
  const a = kills.filter(o => Math.min(4, att(o)) === n && ([3,5].includes(o.ty) ? 1 : 0) === ranged && o.ty !== 10);
  if (a.length < 8) continue;
  const f = (n + 1) / (2 * n);
  console.log(`${n}          ${ranged ? 'ranged' : 'melee '} ${String(a.length).padStart(4)} ${mean(a,o=>o.ptk).toFixed(0).padStart(8)} ${mean(a,o=>o.lost).toFixed(0).padStart(8)}   ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk)).toFixed(2)} | ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk*f)).toFixed(2)}`);
}
for (let n = 1; n <= 4; ++n) {
  const a = kills.filter(o => Math.min(4, att(o)) === n && o.ty === 10);
  if (a.length < 8) continue;
  console.log(`${n}          Varg   ${String(a.length).padStart(4)} ${mean(a,o=>o.ptk).toFixed(0).padStart(8)} ${mean(a,o=>o.lost).toFixed(0).padStart(8)}   ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk)).toFixed(2)} | ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk*(n+1)/(2*n))).toFixed(2)}`);
}
// share 1 (solo) only, melee non-Varg, to isolate the integral effect from the helper share
console.log('\nsolo (share 1, no claimers) melee non-Varg:');
for (let n = 1; n <= 4; ++n) {
  const a = kills.filter(o => Math.min(4, att(o)) === n && ![3,5,10].includes(o.ty) && o.psh === 1 && o.pcl === 0);
  if (a.length < 5) continue;
  const f = (n + 1) / (2 * n);
  console.log(`n=${n} episodes ${a.length} ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk)).toFixed(2)} seq-model ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk*f)).toFixed(2)}  (mean engaged rounds ${mean(a,o=>o.ak).toFixed(1)}, pred kill ${mean(a,o=>o.pk).toFixed(1)})`);
}
