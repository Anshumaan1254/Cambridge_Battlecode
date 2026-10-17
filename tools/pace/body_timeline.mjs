// usage: node seg.mjs file.repl26a TYPEIDX [from] [to] : compressed timeline of one body from trace
import fs from 'fs';
import { unwrapReplay } from '../replay/decode.mjs';
const f = process.argv[2], ty = +process.argv[3], from = +(process.argv[4]||0), to = +(process.argv[5]||9999);
const our = /_B\.repl26a$/.test(f) ? 1 : 0;
const t = unwrapReplay(fs.readFileSync(f), our ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
const names = ['none','farm','capt','wait','trib','home','fight','flee'];
let cur = null; const out = [];
for (const l of t.split('\n')) {
  const s = l.trim(); let m;
  if ((m = s.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\) hp=(\d+) gems=(\d+) gold=(\d+)/)) && +m[2] === ty) {
    const r = +m[1]; if (r < from || r > to) continue;
    const key = m[3] + '/' + m[4];
    if (!cur || cur.key !== key) { if (cur) out.push(cur); cur = { key, r0: r, r1: r, p0: [m[5], m[6]], p1: [m[5], m[6]], gems: m[8], hp: m[7] }; }
    else { cur.r1 = r; cur.p1 = [m[5], m[6]]; cur.gems = m[8]; cur.hp = m[7]; }
  }
  else if ((m = s.match(/^B r=(\d+) (\d+) gems=(\d+) dist=(\d+) need=(\d+) via=(\d+) rb=(\d)/)) && +m[2] === ty && +m[1] >= from && +m[1] <= to) {
    if (cur) { out.push(cur); cur = null; } out.push({ bank: s });
  }
}
if (cur) out.push(cur);
for (const c of out) console.log(c.bank ? '   ' + c.bank : `r${c.r0}-${c.r1} ${names[+c.key.split('/')[0]]} g${c.key.split('/')[1]} (${c.p0})->(${c.p1}) gems=${c.gems} hp=${c.hp}`);
