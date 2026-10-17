// usage: node tools/analysis/time_use.mjs REPLAY...   (LEGEND_TRACE builds: "T r=.. TYPE task=.. g=.. pos=(x,y) hp=.." lines)
// Where body time goes, per champion and overall, from the trace task of every alive turn plus the replay's own events:
//   walk   farm task and the body moved without attacking or casting
//   hit    attacked or cast this turn (any task except fight/flee)
//   stand  farm task, did not move, did not hit (waiting for an ally, blocked, out of range)
//   wait   waiting for a respawn (task wait)          capt  capturing          bank  tribute walk / channel
//   home   walk home / rest on spawn / shop           fight / flee            dead  (from the replay)
// Bench naming: *_B.repl26a = our bot is team B.
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';

const TASK = ['none', 'farm', 'capt', 'wait', 'bank', 'home', 'fight', 'flee'];
const KEYS = ['walk', 'hit', 'stand', 'wait', 'capt', 'bank', 'home', 'fight', 'flee', 'none', 'dead'];
const tot = {};
const add = (k, key) => { (tot[k] ||= Object.fromEntries(KEYS.map((x) => [x, 0])))[key]++; };
for (const f of process.argv.slice(2)) {
  const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const buf = fs.readFileSync(f);
  const d = await decode(unwrapReplay(buf), { every: 1 });
  const txt = unwrapReplay(buf, our ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, '');
  const bodies = d.meta.bodies.filter((b) => b.team === our);
  const typeIdx = Object.fromEntries(bodies.map((b) => [CHAMP.indexOf(b.type), b.index]));
  const acted = new Set();
  for (const e of d.events) if (e.team === our && (e.k === 'Attack' || e.k === 'Cast ability')) acted.add(e.r + ':' + e.who);
  const dead = new Set();
  for (const r of d.rounds) for (const c of r.ch) if (c[1] === our && !c[7]) dead.add(r.r + ':' + c[0]);
  const last = {};
  for (const l0 of txt.split('\n')) {
    const m = l0.trim().match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\)/);
    if (!m) continue;
    const r = +m[1], ty = +m[2], task = TASK[+m[3]] || 'none', who = typeIdx[ty];
    if (who === undefined) continue;
    const name = CHAMP[ty];
    const p = m[5] + ',' + m[6];
    const moved = last[ty] !== undefined && last[ty] !== p;
    last[ty] = p;
    let key;
    if (task === 'fight' || task === 'flee') key = task;
    else if (acted.has(r + ':' + who)) key = 'hit';
    else if (task === 'farm') key = moved ? 'walk' : 'stand';
    else key = task;
    add(name, key); add('ALL', key);
  }
  for (const k of dead) { const who = +k.split(':')[1]; const b = bodies.find((q) => q.index === who); if (b) { add(b.type, 'dead'); add('ALL', 'dead'); } }
}
console.log('share of body-rounds (%)    ' + KEYS.map((k) => k.padStart(6)).join(''));
for (const [k, t] of Object.entries(tot)) {
  const n = Object.values(t).reduce((a, b) => a + b, 0);
  console.log(k.padEnd(12) + String(n).padStart(8) + '      ' + KEYS.map((x) => (100 * t[x] / n).toFixed(1).padStart(6)).join(''));
}
