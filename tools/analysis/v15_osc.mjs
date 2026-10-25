import fs from 'node:fs'; import zlib from 'node:zlib';
const files = process.argv.slice(2);
const cheb=(a,b)=>Math.max(Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1]));
const hist={us:{},them:{}}; let tot={us:0,them:0};
for (const f of files) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
  const FR=d.meta.finalRound; const B=d.meta.bodies;
  const pos=[]; // pos[r][b]=[x,y,alive]
  for (let r=0;r<=FR;r++){ const s=d.rounds[r]; const a=[]; if(s) for(const c of s.ch) a[c[0]]=[c[3],c[4],c[7]]; pos.push(s?a:pos[r-1]); }
  const act=new Set(); // rounds where body attacked/cast
  for (const e of d.events||[]) { if (e.who!==undefined && (e.k==='Attack'||e.k==='Cast ability'||e.k==='Recall'||e.k==='Submit gems')) act.add(e.r*100+e.who); }
  for (let b=0;b<B.length;b++){
    const t=B[b].team; const side=t===0?'us':'them';
    for (let r=10;r<=FR;r+=5){
      let moves=0, ok=true, near=99;
      for (let k=r-9;k<=r;k++){ const p=pos[k][b], q=pos[k-1][b]; if(!p||!q||!p[2]||act.has(k*100+b)){ok=false;break;} if(p[0]!==q[0]||p[1]!==q[1]) moves++;
        for(let o=0;o<B.length;o++) if(B[o].team!==t && pos[k][o] && pos[k][o][2]) near=Math.min(near,cheb(p,pos[k][o])); }
      if(!ok) continue;
      if(moves>=6 && cheb(pos[r][b],pos[r-10][b])<=1){ const key=near<=5?'<=5':near<=8?'6-8':near<=12?'9-12':'>12'; hist[side][key]=(hist[side][key]||0)+1; tot[side]++; }
    }
  }
}
console.log(JSON.stringify(hist), JSON.stringify(tot));
