// Farming-episode time decomposition: predicted (at commit) vs actual, per group class and per champion kit.
// usage: node tools/analysis/xm_fe_time.mjs DIR [DIR...]
import fs from 'fs'; import path from 'path';
import { unwrapReplay } from '../replay/decode.mjs';
const T = ['Ryth','Vesper','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi'];
const RANGED = new Set([1,3,5,6,8,11]);
const P = l => Object.fromEntries(l.trim().split(/\s+/).slice(1).map(x=>x.split('=')).map(([k,v])=>[k,isNaN(+v)?v:+v]));
const FE = [];
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir).filter(f=>f.endsWith('.repl26a'))) {
  const side = f.endsWith('_A.repl26a') ? 'team-a.stdout' : 'team-b.stdout';
  let t; try { t = unwrapReplay(fs.readFileSync(path.join(dir,f)), side).toString('latin1').replace(/\0/g,''); } catch { continue; }
  for (const l of t.split('\n')) if (l.startsWith('FE ')) FE.push(P(l));
}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0), mean=(a,f)=>a.length?sum(a,f)/a.length:NaN;
const cls = o => o.mono ? 'monolith' : o.elk ? 'elk' : o.gems === 0 ? 'gold' : o.n >= 3 && o.pin > 0 ? 'pack' : o.pin > 0 ? 'small' : 'harmless';
const kills = FE.filter(o => o.why === 'kill' && o.plan === 1 && o.eng >= 0);
console.log(`FE ${FE.length}, killed+engaged ${kills.length}`);
console.log('class      n  | pred eta+wait  act commit->engage | pred kill(scaled)  act kill | pred total-6  act commit->dead | ratio');
const groups = {};
for (const o of kills) (groups[cls(o)] ??= []).push(o);
for (const [k, a] of Object.entries(groups)) {
  const pk = o => o.pk * (o.ghpc > 0 ? o.hp0 / o.ghpc : 1);
  const pt = mean(a, o => o.ptime - 6), at = mean(a, o => o.atot);
  console.log(`${k.padEnd(9)} ${String(a.length).padStart(4)} | ${mean(a,o=>o.peta+o.pwait).toFixed(1).padStart(8)} ${mean(a,o=>o.eng-o.commit).toFixed(1).padStart(8)} | ${mean(a,pk).toFixed(1).padStart(8)} ${mean(a,o=>o.ak).toFixed(1).padStart(8)} | ${pt.toFixed(1).padStart(8)} ${at.toFixed(1).padStart(8)} | ${(at/pt).toFixed(2)}`);
}
console.log('\ntravel by kit (no wait, killed+engaged): pred eta (d_tile-1) vs actual commit->engage');
for (let ty = 0; ty < 12; ++ty) {
  const a = kills.filter(o => o.ty === ty && o.pwait === 0 && o.peta > 0);
  if (a.length < 10) continue;
  console.log(`${T[ty].padEnd(8)} ranged=${RANGED.has(ty)?1:0} n ${String(a.length).padStart(4)} pred ${mean(a,o=>o.peta).toFixed(2)} act ${mean(a,o=>o.eng-o.commit).toFixed(2)} diff ${mean(a,o=>o.peta-(o.eng-o.commit)).toFixed(2)} median-diff ${(()=>{const d=a.map(o=>o.peta-(o.eng-o.commit)).sort((x,y)=>x-y);return d[d.length>>1];})()}`);
}
console.log('\nheal-trip model by kit (killed+engaged episodes on groups that fight back)');
for (let ty = 0; ty < 12; ++ty) {
  const a = kills.filter(o => o.ty === ty && o.pin > 0);
  if (a.length < 10) continue;
  console.log(`${T[ty].padEnd(8)} n ${String(a.length).padStart(4)} pred taken ${mean(a,o=>o.ptk).toFixed(0).padStart(5)} act lost ${mean(a,o=>o.lost).toFixed(0).padStart(5)} ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk)).toFixed(2)} | pred trips ${mean(a,o=>o.ptr).toFixed(2)} act trips ${mean(a,o=>o.trips).toFixed(2)} | share ${mean(a,o=>o.psh).toFixed(2)}`);
}
const ends = {}; for (const o of FE) ends[o.why] = (ends[o.why]||0)+1;
console.log('\nends', JSON.stringify(ends));
