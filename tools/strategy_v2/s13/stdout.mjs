import fs from 'fs';
import { unwrapReplay } from '../../replay/decode.mjs';
const raw = fs.readFileSync(process.argv[2]);
try { process.stdout.write(unwrapReplay(raw, process.argv[3] || 'team-a.stdout').toString()); } catch (e) { console.log('err', e.message); }
