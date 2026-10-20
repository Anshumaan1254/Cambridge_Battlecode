import fs from 'node:fs';
import { decode } from '../../replay/decode.mjs';
const [file, ourSide, from] = [process.argv[2], process.argv[3], +process.argv[4]];
const d = await decode(fs.readFileSync(file));
const R = d.rounds;
const us = ourSide === 'A' ? 0 : 1;
console.log('keys', Object.keys(R[0]).join(','), 'champ keys', Object.keys(R[0].champions?.[0] ?? R[0].champs?.[0] ?? {}).join(','));
for (let i = from; i < R.length; i++) {
  const r = R[i];
  const ch = (r.champions ?? r.champs ?? []);
  const line = ch.map(c => `${c.team === us ? 'U' : 'T'}${(c.type ?? '').toString().slice(0,4)}@${c.x ?? c.pos?.x},${c.y ?? c.pos?.y} g${c.gems}${c.alive === false ? ' DEAD' : ''}`).join(' | ');
  console.log(i, JSON.stringify(r.gems ?? r.submitted), line);
}
const ev = d.events.filter(e => e.round >= from && (e.kind === 'capture' || e.step === 'Submit gems' || e.step === 'Gems submitted' || e.type === 'capture'));
for (const e of ev.slice(0, 60)) console.log('EV', JSON.stringify(e));
