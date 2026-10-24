#!/usr/bin/env node
// Big tributes in context (an_fights, bag question): every tribute start with a bag >= 60 gems: champion, round, bag, the team's
// and the enemy's tributed score at the start, whether the bag would end the game (score + bag >= 1000), channel length, outcome
// (done / cancelled: killed, stunned, locked, enemy within 4 when it stopped, other), enemies within 8 at the start and the
// closest enemy during the channel. One JSON line per game.
//   node tools/top2/fights/trib_ctx.mjs SIDES.json C:/battlecode/cache/t2dump/<key>/<game>.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';

const [sidesFile, file] = process.argv.slice(2);
const name = path.basename(file).replace(/\.json\.gz$/, '');
const key = path.basename(path.dirname(file));
const SD = (JSON.parse(fs.readFileSync(sidesFile, 'utf8'))[key] || {})[name];
if (!SD) { console.log(JSON.stringify({ file: path.basename(file), err: 'no side' })); process.exit(0); }
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const FR = d.meta.finalRound;
const TEAM = new Map(d.meta.bodies.map((b) => [b.index, b.team])), TYPE = new Map(d.meta.bodies.map((b) => [b.index, b.type]));
const ROW = new Map();
for (let i = 1; i < d.R.length; ++i) ROW.set(d.R[i][0], d.R[i]);
const row = (r) => { for (let k = r; k >= 1; --k) if (ROW.has(k)) return ROW.get(k); return d.R[1]; };
const pos = (r, b) => row(r)[3].find((c) => c[0] === b);
const subs = d.ev.filter((e) => e.k === 'Submit gems' && e.who !== undefined);
const done = d.ev.filter((e) => e.k === 'Gems submitted' && e.who !== undefined);
const locks = d.ev.filter((e) => e.k === 'Place altar lock' && e.who !== undefined);
const deaths = d.ev.filter((e) => e.k === 'Death');
const out = [];
for (const e of subs) {
  const b = e.who, t = TEAM.get(b), r = Math.min(e.r, FR);
  const me = pos(r - 1, b) || pos(r, b);
  const bag = Math.max(me ? me[6] : 0, pos(r, b) ? pos(r, b)[6] : 0);
  if (bag < 60) continue;
  const dur = Math.max(1, Math.ceil(bag / 10));
  const nxt = subs.find((s) => s.who === b && s.q > e.q);
  const fin = done.find((s) => s.who === b && s.q > e.q && (!nxt || s.q < nxt.q) && s.r <= r + dur + 3);
  const sc = row(r - 1);
  const score = [sc[1], sc[2]];
  const endR = fin ? fin.r : (nxt ? Math.min(nxt.r, r + dur + 1) : r + dur + 1);
  // how did it stop?
  let res = fin ? 'done' : 'cancel', closest = 99, n8 = 0;
  for (const c of row(r - 1)[3]) if (TEAM.get(c[0]) !== t && c[5] && me) { const dd = Math.max(Math.abs(c[1] - me[1]), Math.abs(c[2] - me[2])); if (dd <= 8) n8++; }
  let stopR = endR;
  if (!fin) {
    // the channel stopped at the first round the body acted or moved, died, was stunned, or a lock landed
    stopR = r + dur + 1;
    for (let k = r + 1; k <= Math.min(FR, r + dur + 1); ++k) {
      const p = pos(k, b);
      if (!p || !p[5]) { res = 'killed'; stopR = k; break; }
      if (d.stun.some((s) => s[3] === b && s[1] === k && s[2] >= 0 && TEAM.get(s[2]) !== t)) { res = 'stunned'; stopR = k; break; }
      if (locks.some((l) => TEAM.get(l.who) !== t && l.r === k && l.to && e.to && l.to[0] === e.to[0] && l.to[1] === e.to[1])) { res = 'locked'; stopR = k; break; }
      if (d.ev.some((x) => x.who === b && x.r === k && (x.k === 'Move' || x.k === 'Attack' || x.k === 'Cast ability' || x.k === 'Cancel channel' || x.k === 'Recall'))) { stopR = k; break; }
    }
  }
  for (let k = r; k <= Math.min(FR, stopR); ++k) {
    const p = pos(k, b);
    if (!p) continue;
    for (const c of row(k)[3]) if (TEAM.get(c[0]) !== t && c[5]) closest = Math.min(closest, Math.max(Math.abs(c[1] - p[1]), Math.abs(c[2] - p[2])));
  }
  let closeAtStop = 99;
  if (!fin) { const p = pos(Math.max(r, stopR - 1), b); if (p) for (const c of row(Math.max(r, stopR - 1))[3]) if (TEAM.get(c[0]) !== t && c[5]) closeAtStop = Math.min(closeAtStop, Math.max(Math.abs(c[1] - p[1]), Math.abs(c[2] - p[2]))); }
  if (res === 'cancel' && closeAtStop <= 4) res = 'cancel_enemy_near';
  out.push({ grp: t === SD.st ? 'S' : 'O', ty: TYPE.get(b), r, bag, dur, score: score[t], escore: score[1 - t], wins: score[t] + bag >= 1000 ? 1 : 0, res, n8, closest, stopR: stopR - r,
    endsAfter2000: r + dur > 2000 ? 1 : 0, died: deaths.some((x) => x.who === b && x.r >= r && x.r <= stopR + 1) ? 1 : 0 });
}
console.log(JSON.stringify({ file: path.basename(file), key, game: name, map: SD.map, win: SD.win, FR, trib: out }));
