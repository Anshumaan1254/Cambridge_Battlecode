// usage: node tools/farm/out.mjs FILE.repl26a > out.txt : our team's stdout (side from the _A/_B name)
import fs from 'node:fs';
import { unwrapReplay } from '../replay/decode.mjs';
const f = process.argv[2];
const our = /_B\.repl26a$/.test(f) ? 'team-b.stdout' : 'team-a.stdout';
process.stdout.write(unwrapReplay(fs.readFileSync(f), our).toString('latin1').replace(/\x00/g, ''));
