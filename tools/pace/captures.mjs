import fs from 'fs';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const f = process.argv[2]; const our = /_B\.repl26a$/.test(f) ? 1 : 0;
const d = await decode(unwrapReplay(fs.readFileSync(f)), { every: 1 });
const kinds = {};
for (const e of d.events) if (e.team === our) kinds[e.k] = (kinds[e.k]||0)+1;
console.log(kinds);
const ev = d.events.filter(e => e.team === our && (e.k === 'CaptureGems' || e.k==='Banked'));
console.log(ev.slice(0,80).map(e => `${e.r}:${e.k[0]}${e.gems ?? ''}`).join(' '));
