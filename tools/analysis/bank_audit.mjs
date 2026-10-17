// usage: node tools/analysis/bank_audit.mjs DIR_OR_FILE... (LEGEND_TRACE bundles) : banking time split (walk to altar / stand / submit channel), trips, gems per trip
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const T_TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
const files = process.argv.slice(2).flatMap(p => fs.statSync(p).isDirectory() ? fs.readdirSync(p).filter(f => f.endsWith('.repl26a')).map(f => path.join(p, f)) : [p]);
const A = { walk: 0, stand: 0, trips: 0, banked: 0, alive: 0, homeTrips: 0, viaHome: 0, recallBank: 0, tripWalk: [] };
for (const f of files) {
  const raw = fs.readFileSync(f); const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const text = unwrapReplay(raw, our ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const turns = {};
  for (const l of text.split('\n')) { const m = l.match(/T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\)/); if (m) (turns[T_TYPES[+m[2]]] ||= {})[+m[1]] = { task: +m[3], pos: [+m[5], +m[6]] }; }
  const d = await decode(unwrapReplay(raw), { every: 1 });
  const subs = d.events.filter(e => e.team === our && e.k === 'Submit gems');
  const bank = d.events.filter(e => e.team === our && e.k === 'Banked');
  A.trips += subs.length; A.banked += bank.reduce((s, e) => s + e.gems, 0);
  for (const b of d.meta.bodies.filter(b => b.team === our)) {
    const T = turns[b.type] || {}; let run = 0;
    for (const s of d.rounds) { const c = s.ch.find(q => q[0] === b.index); if (c && c[7] === 1) A.alive++; }
    for (let r = 2; r <= d.meta.finalRound; r++) {
      const t = T[r], p = T[r - 1];
      if (t && t.task === 4) { if (p && Math.max(Math.abs(t.pos[0] - p.pos[0]), Math.abs(t.pos[1] - p.pos[1])) > 0 && Math.max(Math.abs(t.pos[0] - p.pos[0]), Math.abs(t.pos[1] - p.pos[1])) <= 2) { A.walk++; run++; } else A.stand++; }
      else if (run) { A.tripWalk.push(run); run = 0; }
    }
  }
}
A.tripWalk.sort((a, b) => a - b);
console.log(`alive body-rounds ${A.alive}; tribute-task turns walking ${A.walk} (${(100 * A.walk / A.alive).toFixed(1)}%), not moving ${A.stand} (${(100 * A.stand / A.alive).toFixed(1)}%); submits ${A.trips}, banked ${A.banked}, gems/submit ${(A.banked / A.trips).toFixed(1)}; walk runs n=${A.tripWalk.length} median ${A.tripWalk[A.tripWalk.length >> 1]} p90 ${A.tripWalk[Math.floor(A.tripWalk.length * .9)]} mean ${(A.tripWalk.reduce((a, b) => a + b, 0) / A.tripWalk.length).toFixed(1)}`);
