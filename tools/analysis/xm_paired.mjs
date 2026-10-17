// XM_TRACE prediction audit (bots/_x_math built with #define XM_TRACE): before/after errors of the farming model,
// paired on the same episodes (each FE/FR line carries the old and the corrected prediction).
// Paired before/after prediction errors on the new traces (each FE/FR line carries the old and new model).
// usage: node tools/analysis/xm_paired.mjs DIR [DIR...]
import fs from 'fs'; import path from 'path';
import { unwrapReplay } from '../replay/decode.mjs';
const T = ['Ryth','Vesper','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi'];
const P = l => Object.fromEntries(l.trim().split(/\s+/).slice(1).map(x=>x.split('=')).map(([k,v])=>[k,isNaN(+v)?v:+v]));
const FE = [], FR = [];
let games = 0;
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir).filter(f=>f.endsWith('.repl26a'))) {
  const side = f.endsWith('_A.repl26a') ? 'team-a.stdout' : 'team-b.stdout';
  let t; try { t = unwrapReplay(fs.readFileSync(path.join(dir,f)), side).toString('latin1').replace(/\0/g,''); } catch { continue; }
  games++;
  for (const l of t.split('\n')) { if (l.startsWith('FE ')) FE.push(P(l)); else if (l.startsWith('FR ')) FR.push(P(l)); }
}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0), mean=(a,f)=>a.length?sum(a,f)/a.length:NaN;
const stat = (a, pred, act) => `ratio act/pred ${(sum(a,act)/sum(a,pred)).toFixed(3)} bias ${mean(a,o=>pred(o)-act(o)).toFixed(2)} MAE ${mean(a,o=>Math.abs(pred(o)-act(o))).toFixed(2)}`;
console.log(`games ${games}, FE ${FE.length}, FR ${FR.length}`);
// 1. travel
const k = FE.filter(o => o.why === 'kill' && o.plan === 1 && o.eng >= 0);
const tr = k.filter(o => o.pwait === 0 && o.peta0 > 0);
const act = o => o.eng - o.commit;
console.log(`\n[travel] killed episodes, no wait: n ${tr.length}`);
console.log(`  old d-1:      ${stat(tr, o=>o.peta0, act)}`);
console.log(`  new:          ${stat(tr, o=>o.peta, act)}`);
for (const ty of [0,3,4,5,9,10]) { const a = tr.filter(o=>o.ty===ty); if (a.length < 10) continue; console.log(`   ${T[ty].padEnd(8)} n ${String(a.length).padStart(4)} old MAE ${mean(a,o=>Math.abs(o.peta0-act(o))).toFixed(2)} bias ${mean(a,o=>o.peta0-act(o)).toFixed(2)} | new MAE ${mean(a,o=>Math.abs(o.peta-act(o))).toFixed(2)} bias ${mean(a,o=>o.peta-act(o)).toFixed(2)}`); }
// 2. episode damage
const fb = k.filter(o => o.pin > 0);
console.log(`\n[damage over a kill] killed episodes on groups that fight back: n ${fb.length}, mean lost ${mean(fb,o=>o.lost).toFixed(0)}`);
console.log(`  old in x share x kill: ${stat(fb, o=>o.ptk0, o=>o.lost)}`);
console.log(`  new sequential+presence: ${stat(fb, o=>o.ptk, o=>o.lost)}`);
for (const [nm, sel] of [['melee', o=>![3,5,10].includes(o.ty)], ['ranged', o=>[3,5].includes(o.ty)], ['Varg', o=>o.ty===10]]) { const a = fb.filter(sel); console.log(`   ${nm.padEnd(7)} n ${String(a.length).padStart(4)} old ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk0)).toFixed(2)} MAE ${mean(a,o=>Math.abs(o.ptk0-o.lost)).toFixed(0)} | new ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.ptk)).toFixed(2)} MAE ${mean(a,o=>Math.abs(o.ptk-o.lost)).toFixed(0)}`); }
// 3. per-round damage (FR, clean rounds)
const cl = FR.filter(o => o.clean && !o.killed && o.share >= 0 && o.share0 >= 0);
console.log(`\n[damage per round] clean farming rounds: n ${cl.length}, mean lost ${mean(cl,o=>o.lost).toFixed(2)}`);
console.log(`  old in x claim-share: ${stat(cl, o=>o.pin*o.share0, o=>o.lost)}`);
console.log(`  new in x presence-share x reach: ${stat(cl, o=>o.pin*o.share*o.reach, o=>o.lost)}`);
for (const ty of [0,3,4,5,9,10]) { const a = cl.filter(o=>o.ty===ty); if (a.length < 30) continue; console.log(`   ${T[ty].padEnd(8)} n ${String(a.length).padStart(5)} old ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.pin*o.share0)).toFixed(2)} MAE ${mean(a,o=>Math.abs(o.pin*o.share0-o.lost)).toFixed(1)} | new ratio ${(sum(a,o=>o.lost)/sum(a,o=>o.pin*o.share*o.reach)).toFixed(2)} MAE ${mean(a,o=>Math.abs(o.pin*o.share*o.reach-o.lost)).toFixed(1)}`); }
// 4. episode time (travel + wait + kill + capture + trips)
const pt = o => o.peta + o.pwait + o.pk + 6 + o.ptr * o.tc, pt0 = o => o.peta0 + o.pwait + o.pk + 6 + o.ptr0 * o.tc;
console.log(`\n[episode time commit -> capture] killed episodes: n ${k.length}`);
console.log(`  old: ${stat(k, pt0, o=>o.atot+6)}`);
console.log(`  new: ${stat(k, pt, o=>o.atot+6)}`);
const cls = o => o.mono ? 'mono' : o.elk ? 'elk' : o.gems === 0 ? 'gold' : o.n >= 3 && o.pin > 0 ? 'pack' : o.pin > 0 ? 'small' : 'harmless';
for (const c of ['elk','pack','small','gold','harmless','mono']) { const a = k.filter(o=>cls(o)===c); if (a.length < 10) continue; console.log(`   ${c.padEnd(8)} n ${String(a.length).padStart(4)} act/old ${(sum(a,o=>o.atot+6)/sum(a,pt0)).toFixed(2)} | act/new ${(sum(a,o=>o.atot+6)/sum(a,pt)).toFixed(2)}`); }
// 5. trips
const fk = k.filter(o => o.pin > 0);
console.log(`\n[heal trips] n ${fk.length}: actual mean ${mean(fk,o=>o.trips).toFixed(3)} | old pred ${mean(fk,o=>o.ptr0).toFixed(3)} MAE ${mean(fk,o=>Math.abs(o.ptr0-o.trips)).toFixed(3)} | new pred ${mean(fk,o=>o.ptr).toFixed(3)} MAE ${mean(fk,o=>Math.abs(o.ptr-o.trips)).toFixed(3)}`);
// 6. gold value
const gv = FE.filter(o => o.gv !== undefined);
console.log(`\n[gold value at commit] mean ${mean(gv,o=>o.gv).toFixed(3)}; share of commits below 0.22: ${(100*gv.filter(o=>o.gv<0.2199).length/gv.length).toFixed(1)}%; below 0.11: ${(100*gv.filter(o=>o.gv<0.11).length/gv.length).toFixed(1)}%`);
