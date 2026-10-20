import fs from 'fs';
import { decode } from '../../replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2]), { every: 1 });
const from = +process.argv[3] || 0;
for (const e of d.events) if (e.r >= from && ['CaptureGems','Banked','Submit gems','Gems submitted','Recall','Death'].includes(e.k)) console.log(e.r, e.k, e.champ ?? e.who, JSON.stringify(e.to));
const last = d.rounds[d.rounds.length-1]; console.log('final', last.r, JSON.stringify(last.sub));
for (const r of d.rounds) if (r.r >= from && r.r % 10 == 0) console.log('r', r.r, 'sub', JSON.stringify(r.sub), r.ch.filter(c=>c[1]==0).map(c=>`${c[0]}@${c[3]},${c[4]} g${c[8]}`).join(' '));
