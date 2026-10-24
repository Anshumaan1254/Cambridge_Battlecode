#!/usr/bin/env node
// Turns in which a body basic-attacked an enemy champion: the action sequence of the turn (M move, D dash, A attack on a champion,
// K attack on a champion that died this turn, a attack on a camp, R attack-reset cast, C other cast, r recall, s tribute start), whether the attack-reset slot was ready at turn start and used, whether the first attacked
// champion died during the turn, and whether the body ended the turn farther from the nearest enemy (left). One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/pw_fa.mjs replay.repl26a
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../analysis/spell_decode.mjs';
import { KIT } from './pw_kit.mjs';

const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const file = process.argv[2];
let d;
try { d = await decode(fs.readFileSync(file), { endturns: true, rollovers: true }); } catch (e) { process.exit(0); }
const R = new Map(d.rounds.map((x) => [x.r, x]));
const snapBefore = (r) => R.get(r - 1) || R.get(r);
const team = {}, type = {};
for (const b of d.meta.bodies) { team[b.index] = b.team; type[b.index] = b.type; }
let live = {}, curR = -1;
const startRound = (r) => { live = {}; for (const c of snapBefore(r).ch) live[c[0]] = { pos: [c[3], c[4]], alive: !!c[7], hp: c[5], max: c[6] }; };
const nearestEnemy = (tm, p) => { let best = 99; for (const k in live) { const c = live[k]; if (team[k] !== tm && c.alive) best = Math.min(best, cheb(c.pos, p)); } return best; };
const castRounds = {}, lifeStart = {}, killsBy = {};
const turnEv = {}, turnStart = {};
const out = [];
for (const e of d.events) {
  if (e.r !== curR) { curR = e.r; startRound(curR); }
  if (e.k === 'Death') {
    if (live[e.who]) live[e.who].alive = false;
    if (typeof e.by === 'number') (killsBy[e.by] ??= []).push(e.r);
    for (const w in turnEv) for (const x of turnEv[w]) if (x.tgt === e.who && x.k === 'Attack') x.killed = 1;
    continue;
  }
  if (e.who === undefined || e.camp !== undefined) continue;
  const w = e.who;
  if (!turnEv[w] || turnEv[w].length === 0) turnStart[w] = live[w] ? live[w].pos.slice() : null;
  const x = { k: e.k, slot: e.slot };
  (turnEv[w] ??= []).push(x);
  if (e.k === 'Respawn') lifeStart[w] = e.r;
  if (e.k === 'Move' && live[w] && e.to) live[w].pos = e.to;
  if (e.k === 'Attack' && e.to) {
    for (const k in live) { const c = live[k]; if (team[k] !== team[w] && c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1]) { x.tgt = +k; x.champ = 1; } }
  }
  if (e.k === 'Cast ability') {
    const kind = KIT[type[w]]?.[e.slot];
    x.kind = kind;
    if ((kind === 'dash' || kind === 'hordash') && e.to && live[w]) live[w].pos = e.to.slice();
    ((castRounds[w] ??= [[], []])[e.slot]).push(e.r);
  }
  if (e.k === 'End turn') {
    const acts = turnEv[w] || [];
    turnEv[w] = [];
    const r = e.r;
    if (!acts.some((a) => a.k === 'Attack' && a.champ)) continue;
    const kit = KIT[type[w]] || [];
    const rs = kit.findIndex((k) => k === 'reset' || k === 'ereset');
    const ready = [0, 1].map((s) => {
      const h = castRounds[w]?.[s] || [];
      let last = -100;
      for (let k = h.length - 1; k >= 0; k--) if (h[k] < r) { last = h[k]; break; }
      if ((lifeStart[w] ?? -1) > last) last = -100;
      if (type[w] === 'Vendetta' && (killsBy[w] || []).some((kr) => kr >= last && kr < r)) last = -100;
      return r - last >= 8 ? 1 : 0;
    });
    const seq = acts.filter((a) => ['Move', 'Attack', 'Cast ability', 'Recall', 'Submit gems'].includes(a.k)).map((a) => {
      if (a.k === 'Move') return 'M';
      if (a.k === 'Attack') return a.champ ? (a.killed ? 'K' : 'A') : 'a';
      if (a.k === 'Cast ability') return a.kind === 'dash' || a.kind === 'hordash' ? 'D' : (a.slot === rs ? 'R' : 'C');
      return a.k === 'Recall' ? 'r' : 's';
    }).join('');
    const sp = turnStart[w] || live[w]?.pos;
    const dE = sp ? nearestEnemy(team[w], sp) : 99;
    const dEnd = live[w] ? nearestEnemy(team[w], live[w].pos) : 99;
    const me = live[w];
    out.push([w, r, rs >= 0 ? ready[rs] : -1, ready[0], ready[1], seq, dEnd > dE ? 1 : 0, me ? +(me.hp / me.max).toFixed(2) : null]);
  }
}
console.log(JSON.stringify({ file: path.basename(file), bodies: d.meta.bodies.map((b) => [b.index, b.team, b.type]), turns: out }));
