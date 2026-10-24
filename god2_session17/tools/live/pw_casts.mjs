#!/usr/bin/env node
// Ability ("powers") usage per body from a replay: every cast with its target class and context, per-turn slot readiness
// (ready = alive, not channelling / stunned / rolled over, >= 8 rounds since the slot's last cast in this life), and
// per-body champion engagements (rounds where the body hit or was hit by an enemy champion, gaps <= 3 merged) with
// when each slot was used relative to the first exchange and the local outcome within 15 rounds.
// One JSON line per replay (aggregate with tools/live/pw_agg.py).
//   CAMBC_CACHE=... node tools/live/pw_casts.mjs replay.repl26a
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../analysis/spell_decode.mjs';

// slot kinds: unit spells target one tile (dmg, stun, dmgstun); area spells radius 1 (aoestun, aoe); hordash = dash + radius-1
// landing hit + stun; dash = 2-step move; reset / ereset (Marcella: next attack stuns) / shield = self; heal = ally.
export const KIT = {
  Ryth: ['aoestun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'stun'],
  Issac: ['reset', 'dash'], Stellar: ['dmg', 'aoe'], Prism: ['dmgstun', 'aoe'], Marcella: ['ereset', 'dmg'],
  Willow: ['heal', 'reset'], Ren: ['dmgstun', 'dash'], Varg: ['reset', 'shield'], Tavi: ['reset', 'dmgstun'],
  HeartOfRuin: ['shield', 'hordash'],
};
const UNIT = new Set(['dmg', 'stun', 'dmgstun']);
const AREA = new Set(['aoestun', 'aoe', 'hordash']);
const STUNS = new Set(['stun', 'dmgstun', 'aoestun', 'hordash']);
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const radOf = (k) => (AREA.has(k) ? 1 : 0);

const file = process.argv[2];
let d;
try { d = await decode(fs.readFileSync(file), { endturns: true, rollovers: true }); } catch (e) { process.exit(0); }
const R = new Map(d.rounds.map((x) => [x.r, x]));
const snapBefore = (r) => R.get(r - 1) || R.get(r);
const bodies = d.meta.bodies;
const team = {}, type = {};
for (const b of bodies) { team[b.index] = b.team; type[b.index] = b.type; }
const camps = d.meta.camps;
const evs = d.events;

let live = {};
let curR = -1;
let campHp = [];
const ended = new Set();
const startRound = (r) => {
  const s = snapBefore(r);
  live = {};
  for (const c of s.ch) live[c[0]] = { pos: [c[3], c[4]], alive: !!c[7], hp: c[5], max: c[6], gems: c[8] };
  campHp = s.campHp.slice();
  ended.clear();
};
const enemiesNear = (tm, p, rad) => { const o = []; for (const k in live) { const c = live[k]; if (team[k] !== tm && c.alive && cheb(c.pos, p) <= rad) o.push(+k); } return o; };
const alliesNear = (tm, p, rad, self) => { let n = 0; for (const k in live) { const c = live[k]; if (+k !== self && team[k] === tm && c.alive && cheb(c.pos, p) <= rad) n++; } return n; };
const nearestEnemy = (tm, p) => { let best = 99, who = -1; for (const k in live) { const c = live[k]; if (team[k] !== tm && c.alive) { const dd = cheb(c.pos, p); if (dd < best) { best = dd; who = +k; } } } return [best, who]; };
const campsNear = (p, rad) => { let n = 0; for (let i = 0; i < camps.length; i++) if (campHp[i] > 0 && cheb([camps[i].x, camps[i].y], p) <= rad) n++; return n; };
const nearestCamp = (p) => { let best = 99; for (let i = 0; i < camps.length; i++) if (campHp[i] > 0) best = Math.min(best, cheb([camps[i].x, camps[i].y], p)); return best; };

const casts = [];
const hitsBy = {}; // w -> [{r, v, k}] w hit enemy champion v
const hitsOn = {}; // w -> [{r, a}] w hit by enemy champion a (attack or spell)
const campHitOn = {}; // w -> [r]
const exch = {}; // w -> Set(rounds)
const deaths = [];
const chanUntil = {}, chanKind = {}, stunLost = {}, rolled = {};
const lastCast = {}; // w -> [r0, r1]
const castRounds = {}; // w -> [[rounds slot0], [rounds slot1]]
const turnEv = {};
const turnRec = {}; // w -> Map(r -> {ready:[b,b], cast:[b,b], e4, e6, camp4, atk, atkChamp, mv, usable})
const lifeStart = {};
const addHit = (a, v, r, k) => {
  (hitsBy[a] ??= []).push({ r, v, k }); (hitsOn[v] ??= []).push({ r, a, k });
  (exch[a] ??= new Set()).add(r); (exch[v] ??= new Set()).add(r);
};

for (let i = 0; i < evs.length; i++) {
  const e = evs[i];
  if (e.r !== curR) { curR = e.r; startRound(curR); }
  if (e.k === 'Death') {
    if (live[e.who]) live[e.who].alive = false;
    deaths.push({ r: e.r, who: e.who, team: team[e.who], at: e.at, by: e.by, bag: e.bag || 0 });
    if (typeof e.by === 'number' && type[e.by] === 'Vendetta') lastCast[e.by] = [-100, -100];
    lastCast[e.who] = [-100, -100];
    continue;
  }
  if (e.camp !== undefined) {
    if (e.k === 'Attack' && e.to) for (const k in live) { const c = live[k]; if (c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1]) (campHitOn[k] ??= []).push(e.r); }
    continue;
  }
  if (e.who === undefined) continue;
  const w = e.who;
  (turnEv[w] ??= []).push(e);
  if (e.k === 'Respawn') { if (live[w]) { live[w].alive = true; const q = (R.get(e.r) || snapBefore(e.r)).ch.find((c) => c[0] === w); if (q) live[w].pos = [q[3], q[4]]; } lastCast[w] = [-100, -100]; lifeStart[w] = e.r; }
  if (e.k === 'Move' && live[w] && e.to) live[w].pos = e.to;
  if (e.k === 'Recall') { chanUntil[w] = e.r + 4; chanKind[w] = 'recall'; }
  if (e.k === 'Submit gems') { chanUntil[w] = e.r + Math.max(1, Math.ceil((live[w]?.gems || 0) / 10)) - 1; chanKind[w] = 'tribute'; }
  if (e.k === 'Teleport channel') { chanUntil[w] = e.r + 2; chanKind[w] = 'tp'; }
  if (e.k === 'Cancel channel') chanUntil[w] = e.r - 1;
  if (e.k === 'Turn rollover') { rolled[`${w}:${e.r}`] = 1; rolled[`${w}:${e.r + 1}`] = 1; }
  if (e.k === 'Attack' && e.to) {
    for (const k in live) { const c = live[k]; if (team[k] !== team[w] && c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1]) addHit(w, +k, e.r, 'atk'); }
  }
  if (e.k === 'Cast ability') {
    const kind = KIT[type[w]]?.[e.slot] || '?';
    const me = live[w];
    const from = me ? me.pos.slice() : (e.from || [0, 0]);
    const [dE, nE] = nearestEnemy(team[w], from);
    const rec = { r: e.r, w, slot: e.slot, kind, ab: e.ability, hp: me ? +(me.hp / me.max).toFixed(2) : null, gems: me?.gems || 0,
      dE, e4: enemiesNear(team[w], from, 4).length, e8: enemiesNear(team[w], from, 8).length, a4: alliesNear(team[w], from, 4, w),
      dCamp: nearestCamp(from) };
    if (UNIT.has(kind) || AREA.has(kind)) {
      if (e.to) {
        const ch = enemiesNear(team[w], e.to, radOf(kind));
        const cp = campsNear(e.to, radOf(kind));
        rec.nCh = ch.length; rec.nCamp = cp; rec.cls = ch.length ? 'champ' : (cp ? 'camp' : 'empty');
        rec.tgt = ch.length ? ch.map((t) => type[t]) : undefined;
        for (const t of ch) addHit(w, t, e.r, 'spell');
        if (STUNS.has(kind)) for (const t of ch) {
          const after = ended.has(t);
          const lost = after ? e.r + 1 : e.r;
          stunLost[`${t}:${lost}`] = 1;
          const tc = live[t];
          (rec.stun ??= []).push({ t, tt: type[t], after: after ? 1 : 0, lost, chan: (chanUntil[t] ?? -99) >= e.r ? (chanKind[t] || 'ch') : 0,
            tgems: tc.gems, thp: +(tc.hp / tc.max).toFixed(2), idx: i });
        }
      } else rec.cls = 'noto';
      if (kind === 'hordash' && e.to) {
        rec.dash = { dist: cheb(from, e.to), dBefore: dE, dAfter: nE >= 0 && live[nE] ? cheb(live[nE].pos, e.to) : 99, nearAfter: nearestEnemy(team[w], e.to)[0], campBefore: nearestCamp(from), campAfter: nearestCamp(e.to) };
      }
    } else if (kind === 'dash') {
      if (e.to) rec.dash = { dist: cheb(from, e.to), dBefore: dE, dAfter: nE >= 0 && live[nE] ? cheb(live[nE].pos, e.to) : 99, nearAfter: nearestEnemy(team[w], e.to)[0], campBefore: nearestCamp(from), campAfter: nearestCamp(e.to) };
      rec.cls = 'move';
    } else if (kind === 'heal') {
      rec.cls = 'ally';
      if (e.to) {
        for (const k in live) { const c = live[k]; if (team[k] === team[w] && +k !== w && c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1]) { rec.ally = type[k]; rec.allyHp = +(c.hp / c.max).toFixed(2); rec.allyMiss = c.max - c.hp; rec.allyE4 = enemiesNear(team[w], c.pos, 4).length; } }
      }
    } else rec.cls = 'self';
    if ((kind === 'dash' || kind === 'hordash') && e.to && me) me.pos = e.to.slice();
    casts.push(rec);
    (lastCast[w] ??= [-100, -100])[e.slot] = e.r;
    ((castRounds[w] ??= [[], []])[e.slot]).push(e.r);
    rec.ti = (turnEv[w].length - 1); // position in the turn's event list
    e._rec = rec;
  }
  if (e.k === 'End turn') {
    ended.add(w);
    const acts = turnEv[w] || [];
    turnEv[w] = [];
    const r = e.r;
    const me = live[w];
    const prevS = snapBefore(r);
    const pc = prevS.ch.find((c) => c[0] === w);
    const aliveTurn = (pc && pc[7]) || acts.some((a) => a.k === 'Respawn');
    if (!aliveTurn || !me || !me.alive) continue;
    const startedChan = acts.some((a) => a.k === 'Recall' || a.k === 'Submit gems' || a.k === 'Teleport channel');
    const chan = (chanUntil[w] ?? -99) >= r && !startedChan;
    const stunned = !!stunLost[`${w}:${r}`];
    const roll = !!rolled[`${w}:${r}`];
    const usable = !chan && !stunned && !roll;
    const firstMv = acts.find((a) => (a.k === 'Move' || (a.k === 'Cast ability' && (KIT[type[w]][a.slot] === 'dash' || KIT[type[w]][a.slot] === 'hordash'))) && a.from);
    const sp = firstMv && firstMv.from[0] >= 0 && !(firstMv.k === 'Cast ability' && firstMv.from[0] === 0 && firstMv.from[1] === 0) ? firstMv.from : me.pos;
    const [dE] = nearestEnemy(team[w], sp);
    const atks = acts.filter((a) => a.k === 'Attack');
    let atkChamp = 0;
    for (const a of atks) if (a.to && (hitsBy[w] || []).some((h) => h.r === r && h.k === 'atk')) atkChamp = 1;
    const cs = acts.filter((a) => a.k === 'Cast ability');
    const rec = { usable, chan, stunned, roll, dE, camp4: campsNear(sp, 4) > 0 ? 1 : 0, atk: atks.length, atkChamp,
      mv: acts.some((a) => a.k === 'Move') ? 1 : 0, ready: [0, 0], cast: [0, 0], anyCast: cs.length ? 1 : 0, hp: +(me.hp / me.max).toFixed(2), dEnd: nearestEnemy(team[w], me.pos)[0],
      fight: exch[w]?.has(r - 1) || exch[w]?.has(r - 2) || (hitsOn[w] || []).some((h) => h.r === r) ? 1 : 0 };
    rec.sinceLast = [0, 0];
    for (const s of [0, 1]) {
      rec.cast[s] = cs.filter((a) => a.slot === s).length;
      const h = castRounds[w]?.[s] || [];
      let last = -100;
      for (let k = h.length - 1; k >= 0; k--) if (h[k] < r) { last = h[k]; break; }
      if ((lifeStart[w] ?? -1) > last) last = -100;
      // Vendetta: a kill by w after `last` resets her cooldowns
      if (type[w] === 'Vendetta' && deaths.some((dd) => dd.by === w && dd.r >= last && dd.r < r)) last = -100;
      rec.ready[s] = usable && r - last >= 8 ? 1 : 0;
      rec.sinceLast[s] = Math.min(99, r - last);
    }
    // reset usage detail: attacks before / after the cast in this turn
    for (const c of cs) {
      const kind = KIT[type[w]][c.slot];
      if (kind === 'reset' || kind === 'ereset') {
        const ci = acts.indexOf(c);
        const before = acts.slice(0, ci).filter((a) => a.k === 'Attack').length, after = acts.slice(ci + 1).filter((a) => a.k === 'Attack').length;
        c._rec.atkBefore = before; c._rec.atkAfter = after; c._rec.atkChamp = atkChamp;
      }
      if (kind === 'dash' || kind === 'hordash') {
        const ci = acts.indexOf(c);
        c._rec.atkAfter = acts.slice(ci + 1).filter((a) => a.k === 'Attack').length;
        c._rec.atkBefore = acts.slice(0, ci).filter((a) => a.k === 'Attack').length;
        c._rec.mvBefore = acts.slice(0, ci).filter((a) => a.k === 'Move').length;
        c._rec.mvAfter = acts.slice(ci + 1).filter((a) => a.k === 'Move').length;
      }
    }
    (turnRec[w] ??= new Map()).set(r, rec);
  }
}

// stun follow-ups and kills
for (const c of casts) for (const s of c.stun || []) {
  let focus = 0;
  for (let j = s.idx + 1; j < evs.length && evs[j].r <= s.lost; j++) {
    const x = evs[j];
    if ((x.k === 'Attack' || x.k === 'Cast ability') && x.who !== undefined && team[x.who] === team[c.w] && x.to) {
      const tc = snapBefore(x.r).ch.find((q) => q[0] === s.t);
      if (tc && cheb([tc[3], tc[4]], x.to) <= 1) focus++;
    }
  }
  s.focus = focus;
  s.kill3 = deaths.some((dd) => dd.who === s.t && dd.r >= c.r && dd.r <= c.r + 3) ? 1 : 0;
  delete s.idx;
}

// engagements per body
const episodes = [];
for (const w in exch) {
  const rs = [...exch[w]].sort((a, b) => a - b);
  let cur = null;
  const flush = () => { if (cur) episodes.push(cur); };
  for (const r of rs) {
    if (cur && r - cur.e <= 3) { cur.e = r; cur.n++; }
    else { flush(); cur = { w: +w, s: r, e: r, n: 1 }; }
  }
  flush();
}
const casts_by = {};
for (const c of casts) (casts_by[c.w] ??= []).push(c);
for (const ep of episodes) {
  const w = ep.w, s = ep.s;
  ep.team = team[w]; ep.champ = type[w];
  const st = snapBefore(s);
  const me = st.ch.find((c) => c[0] === w);
  const pos = me ? [me[3], me[4]] : [0, 0];
  ep.hp = me ? +(me[5] / me[6]).toFixed(2) : null;
  ep.nE = st.ch.filter((c) => c[1] !== team[w] && c[7] && cheb([c[3], c[4]], pos) <= 6).length;
  ep.nA = st.ch.filter((c) => c[1] === team[w] && c[0] !== w && c[7] && cheb([c[3], c[4]], pos) <= 6).length;
  ep.hpE = st.ch.filter((c) => c[1] !== team[w] && c[7] && cheb([c[3], c[4]], pos) <= 6).reduce((a, c) => a + c[6], 0);
  ep.hpA = st.ch.filter((c) => c[1] === team[w] && c[7] && cheb([c[3], c[4]], pos) <= 6).reduce((a, c) => a + c[6], 0);
  const firstBy = (hitsBy[w] || []).filter((h) => h.r === s).length, firstOn = (hitsOn[w] || []).filter((h) => h.r === s).length;
  ep.first = firstBy && !firstOn ? 'me' : (!firstBy && firstOn ? 'them' : 'both');
  ep.hitsBy = (hitsBy[w] || []).filter((h) => h.r >= s && h.r <= ep.e).length;
  ep.hitsOn = (hitsOn[w] || []).filter((h) => h.r >= s && h.r <= ep.e).length;
  const tr = turnRec[w]?.get(s) || turnRec[w]?.get(s + 1);
  ep.slots = [0, 1].map((sl) => {
    // readiness at the start: ready on the turn of round s, or cast in s-2..s-1 (then it was ready before)
    const pre = (casts_by[w] || []).filter((c) => c.slot === sl && c.r >= s - 2 && c.r <= ep.e + 1);
    const ready = tr ? tr.ready[sl] : 0;
    const off = pre.length ? pre[0].r - s : null;
    return { ready: ready || (off !== null && off < 0) ? 1 : 0, off, n: pre.length, lc: tr ? tr.sinceLast?.[sl] : null };
  });
  ep.kills = deaths.filter((dd) => dd.team !== team[w] && dd.r >= s && dd.r <= s + 15 && dd.at && cheb(dd.at, pos) <= 10).length;
  ep.deaths = deaths.filter((dd) => dd.team === team[w] && dd.r >= s && dd.r <= s + 15 && dd.at && cheb(dd.at, pos) <= 10).length;
  ep.died = deaths.some((dd) => dd.who === w && dd.r >= s && dd.r <= s + 15) ? 1 : 0;
  ep.killedVictim = (hitsBy[w] || []).filter((h) => h.r >= s && h.r <= ep.e).some((h) => deaths.some((dd) => dd.who === h.v && dd.r >= s && dd.r <= s + 15)) ? 1 : 0;
}
for (const c of casts) {
  const ep = episodes.find((x) => x.w === c.w && c.r >= x.s - 2 && c.r <= x.e + 1);
  c.ep = ep ? c.r - ep.s : null;
  delete c.ti;
}

// per-body per-slot turn statistics
const bstats = [];
for (const b of bodies) {
  const m = turnRec[b.index];
  if (!m) continue;
  // context buckets per turn: ex = this body hit / was hit by an enemy champion this round; e4 / e6 / e9 = nearest enemy champion at
  // turn start within 4 / 5-6 / 7-9; far = farther. Per slot and bucket: usable turns, ready turns, casts, ready-but-idle turns (no cast
  // of any slot), blocked (ready, other slot cast this turn).
  // in a fight = this body hit or was hit by an enemy champion in the previous 2 rounds, or was hit earlier this round (independent of
  // its own action this turn). fA = in a fight and attacked an enemy champion this turn; f4 = in a fight, no champion attack, enemy
  // within 4 at turn start; fF = in a fight, nearest enemy farther than 4; oA = not in a fight, attacked a champion (opening hit);
  // e4 / e6 / e9 / far = not in a fight, no champion attack, nearest enemy within 4 / 5-6 / 7-9 / farther.
  const B = ['fA', 'f4', 'fF', 'oA', 'e4', 'e6', 'e9', 'far'];
  const z = { i: b.index, team: b.team, champ: b.type, alive: 0, usable: 0, chan: 0, stun: 0, roll: 0, ctx: Object.fromEntries(B.map((k) => [k, 0])),
    sl: [0, 1].map(() => ({ ready: 0, casts: 0, idle: 0, blocked: 0, gapSum: 0, gapN: 0, idleAtk: 0, campSafeIdle: 0, idleFlee: 0,
      c: Object.fromEntries(B.map((k) => [k, [0, 0, 0, 0]])) })) }; // [ready, cast, idle, blocked]
  const ex = exch[b.index] || new Set();
  for (const [r, t] of m) {
    z.alive++; if (t.chan) z.chan++; if (t.stunned) z.stun++; if (t.roll) z.roll++;
    if (!t.usable) continue;
    z.usable++;
    const bk = t.atkChamp ? (t.fight ? 'fA' : 'oA') : t.fight ? (t.dE <= 4 ? 'f4' : 'fF') : (t.dE <= 4 ? 'e4' : (t.dE <= 6 ? 'e6' : (t.dE <= 9 ? 'e9' : 'far')));
    z.ctx[bk]++;
    for (const s of [0, 1]) {
      const q = z.sl[s];
      q.casts += t.cast[s];
      if (t.cast[s] && t.sinceLast[s] < 99) { q.gapSum += Math.max(0, t.sinceLast[s] - 8); q.gapN++; }
      if (!t.ready[s]) { if (t.cast[s]) q.c[bk][1]++; continue; }
      q.ready++; q.c[bk][0]++;
      if (t.cast[s]) { q.c[bk][1]++; continue; }
      if (t.anyCast) { q.blocked++; q.c[bk][3]++; continue; }
      q.idle++; q.c[bk][2]++;
      if (t.atk) q.idleAtk++;
      if (bk === 'far' && t.camp4) q.campSafeIdle++;
      if (t.fight && t.dEnd > t.dE) q.idleFlee++;
    }
  }
  bstats.push(z);
}

// compact cast rows
const cols = ['r', 'w', 'slot', 'kind', 'cls', 'hp', 'gems', 'dE', 'e4', 'e8', 'a4', 'dCamp', 'nCh', 'nCamp', 'ep', 'atkBefore', 'atkAfter', 'atkChamp', 'mvBefore', 'mvAfter'];
const rows = casts.map((c) => {
  const o = {};
  for (const k of cols) if (c[k] !== undefined && c[k] !== null) o[k] = c[k];
  if (c.dash) o.dash = c.dash;
  if (c.stun) o.stun = c.stun;
  if (c.tgt) o.tgt = c.tgt;
  if (c.ally) { o.ally = c.ally; o.allyHp = c.allyHp; o.allyMiss = c.allyMiss; o.allyE4 = c.allyE4; }
  // shield: hits taken around the cast
  if (c.kind === 'shield') {
    const hs = (hitsOn[c.w] || []).map((h) => h.r);
    const chs = campHitOn[c.w] || [];
    o.hitPre = hs.filter((x) => x >= c.r - 1 && x <= c.r).length + chs.filter((x) => x >= c.r - 1 && x <= c.r).length;
    o.hitPost = hs.filter((x) => x > c.r && x <= c.r + 5).length;
    o.campPost = chs.filter((x) => x > c.r && x <= c.r + 5).length;
  }
  return o;
});
console.log(JSON.stringify({ file: path.basename(file), W: d.meta.width, H: d.meta.height, outcome: d.meta.outcome, fr: d.meta.finalRound,
  bodies: bodies.map((b) => [b.index, b.team, b.type]), casts: rows, bstats, episodes, deaths: deaths.map((x) => [x.r, x.who, x.team, x.by]) }));
