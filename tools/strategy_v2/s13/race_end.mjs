import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const [file, side, from] = [process.argv[2], process.argv[3], +process.argv[4]];
const d = await decode(fs.readFileSync(file));
const us = side === 'A' ? 0 : 1;
const names = d.meta.bodies.map(b => (b.team === us ? 'u' : 't') + b.type.slice(0, 3));
for (const r of d.rounds.slice(from)) {
  console.log(r.r, 'sub', r.sub.join('-'), r.ch.map(c => `${names[c[0]]}(${c[3]},${c[4]})${c[8] ? 'g' + c[8] : ''}${c[7] ? '' : 'X'}`).join(' '));
}
const kinds = new Set(['Banked', 'Captured', 'Capture', 'Recall', 'Teleport complete', 'Gems submitted']);
for (const e of d.events) if (e.r >= from && (kinds.has(e.k) || /aptur/.test(e.k))) console.log('EV', e.r, e.k, names[e.who] ?? '', e.gems ?? '', JSON.stringify(e.at ?? e.to ?? ''));
