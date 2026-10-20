import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2]));
const r = d.rounds[340];
console.log(JSON.stringify(r).slice(0, 1500));
console.log(JSON.stringify(d.events.slice(-5)).slice(0, 1500));
console.log(JSON.stringify(d.meta).slice(0, 800));
