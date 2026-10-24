#!/usr/bin/env node
// Ability use per body from a fight dump (tools/live/fightdump.mjs format; effects attributed exactly by step q):
// casts per slot with the effect class (champion hit / camp hit / ally heal / self / empty; dashes travel / engage / escape /
// lateral) and the turn context (F fight = hit or was hit by an enemy champion in the last 2 rounds or earlier this round,
// N enemy champion within 5, C working a camp, O other); ready-slot use per context (ready = alive, not stunned, not in an
// uncancelled channel, >= 8 rounds since the slot's last cast in this life; Vendetta champion kills reset); action sequences
// of champion-attack turns (M move, D dash, A attack hitting an enemy champion, K killing hit, a camp hit, R attack reset,
// C other cast, r recall, s tribute); shields (pre-emptive or reactive), heals, stuns on enemy champions with the victim's
// channel (tribute / recall), Prism casts by carried bag. One JSON line per dump.
//   node tools/top2/items/ab.mjs dump.json.gz
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { KIT } from '../../live/pw_kit.mjs';

const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.error(file, e.message); process.exit(0); }
const bodies = d.meta.bodies;
const team = {}, type = {};
for (const b of bodies) { team[b.index] = b.team; type[b.index] = b.type; }
const R = new Map(d.R.map((x) => [x[0], x]));
const final = d.meta.finalRound;
const st = (r, w) => { for (let k = r; k >= 0; --k) { const s = R.get(k); if (s) { const c = s[3].find((q) => q[0] === w); if (c) return c; } } return null; };
const stateAt = (r) => { for (let k = r; k >= 0; --k) if (R.has(k)) return R.get(k)[3]; return d.R[0][3]; };
const posOf = (c) => [c[1], c[2]];
const nearestEnemy = (S, tm, p) => { let b = 99; for (const c of S) if (c[5] && team[c[0]] !== tm) b = Math.min(b, cheb(posOf(c), p)); return b; };
const enemiesWithin = (S, tm, p, rad) => S.filter((c) => c[5] && team[c[0]] !== tm && cheb(posOf(c), p) <= rad);

// effects by step
const byQ = (arr) => { const m = new Map(); for (const x of arr) { if (!m.has(x[0])) m.set(x[0], []); m.get(x[0]).push(x); } return m; };
const dmgQ = byQ(d.dmg), cdmgQ = byQ(d.cdmg), stunQ = byQ(d.stun), healQ = byQ(d.heal);
// exchanges: rounds where a body hit / was hit by an enemy champion
const exch = {}, hitOnQ = {}; // hitOnQ[w] = [[q, r, attacker]]
const dmgTaken = {}; // w -> [[q, r]] any damage (champion or camp)
for (const x of d.dmg) {
  const [q, r, a, v] = x;
  (dmgTaken[v] ??= []).push([q, r]);
  if (a < 0 || a === v || team[a] === team[v]) continue;
  (exch[a] ??= new Set()).add(r); (exch[v] ??= new Set()).add(r);
  (hitOnQ[v] ??= []).push([q, r, a]);
}
const deaths = d.ev.filter((e) => e.k === 'Death');
// events per body per round
const turns = new Map(); // key w*4096+r -> events
for (const e of d.ev) {
  if (e.who === undefined || e.k === 'Death' || e.k === 'CaptureGems' || e.k === 'Banked') continue;
  const k = e.who * 4096 + e.r;
  if (!turns.has(k)) turns.set(k, []);
  turns.get(k).push(e);
}
// stunned turns: the victim loses its next turn (this round if it has not acted yet)
const lost = new Set();
for (const [q, r, a, v] of d.stun) {
  const acts = turns.get(v * 4096 + r) || [];
  const acted = acts.some((e) => e.q < q);
  lost.add(v * 4096 + (acted ? r + 1 : r));
}

const stunR = new Map();
for (const x of d.stun) { if (!stunR.has(x[1])) stunR.set(x[1], []); stunR.get(x[1]).push(x); }
const chanEv = {}, recalls = {}, aliveN = {};
for (const e of d.ev) {
  if (e.who === undefined) continue;
  if (['Recall', 'Submit gems', 'Cancel channel', 'Gems submitted'].includes(e.k)) (chanEv[e.who] ??= []).push(e);
  if (e.k === 'Recall') recalls[e.who] = (recalls[e.who] || 0) + 1;
}
for (const k in chanEv) chanEv[k].sort((a, b) => a.q - b.q);
for (const b of bodies) { recalls[b.index] ??= 0; aliveN[b.index] = d.R.filter((x) => x[3].some((c) => c[0] === b.index && c[5])).length; }

const B = {};
for (const b of bodies) {
  B[b.index] = {
    i: b.index, t: b.team, ty: b.type, alive: 0, usable: 0, ctx: { F: 0, N: 0, C: 0, O: 0 },
    sl: [0, 1].map(() => ({ casts: 0, cls: {}, cctx: { F: 0, N: 0, C: 0, O: 0 }, ready: { F: 0, N: 0, C: 0, O: 0 }, rcast: { F: 0, N: 0, C: 0, O: 0 }, idle: { F: 0, N: 0, C: 0, O: 0 }, wait: 0, waitN: 0 })),
    atk: { turns: 0, ready: 0, used: 0, seq: {}, left: 0 }, shield: { n: 0, pre: 0, en4: 0, hit5: 0, fight: 0 }, heal: { n: 0, miss: 0, frac: 0, fight: 0, self: 0 },
    stun: { n: 0, trib: 0, tribBag: 0, recall: 0, kill3: 0, ex: [] }, dmg: { atkCh: 0, castCh: 0, castCamp: 0, atkCamp: 0 },
    prism: { bag: {}, dmgCh: {}, dmgCamp: {}, bagRounds: {}, bagFight: {} }, ex: {},
  };
}
const bagB = (g) => (g === 0 ? '0' : g < 25 ? '1-24' : g < 50 ? '25-49' : g < 100 ? '50-99' : g < 200 ? '100-199' : '200+');

// channel state per body (open recall / tribute / teleport)
const chan = {}; // w -> {k, r}
const lastCast = {}; // w -> [r0, r1]
const lifeStart = {};
const prevAlive = {};
for (const b of bodies) { lastCast[b.index] = [-100, -100]; prevAlive[b.index] = 1; }

for (let r = 1; r <= final; ++r) {
  const S0 = stateAt(r - 1), S1 = stateAt(r);
  for (const b of bodies) {
    const w = b.index, tm = team[w], X = B[w];
    const c0 = S0.find((q) => q[0] === w), c1 = S1.find((q) => q[0] === w);
    if (!c0 || !c1) continue;
    if (!c0[5] && c1[5]) { lifeStart[w] = r; lastCast[w] = [-100, -100]; delete chan[w]; }
    if (!c0[5] && !c1[5]) continue;
    const acts = (turns.get(w * 4096 + r) || []).sort((a, b2) => a.q - b2.q);
    if (c0[5]) X.alive++;
    // bag stats (Prism)
    if (type[w] === 'Prism' && c0[5]) {
      const bb = bagB(c0[6]);
      X.prism.bagRounds[bb] = (X.prism.bagRounds[bb] || 0) + 1;
      if (exch[w]?.has(r)) X.prism.bagFight[bb] = (X.prism.bagFight[bb] || 0) + 1;
    }
    const firstQ = acts.length ? acts[0].q : Infinity;
    const p0 = c0[5] ? posOf(c0) : (acts.find((e) => e.from)?.from || posOf(c1));
    const dE = nearestEnemy(S0, tm, p0);
    const fight = exch[w]?.has(r - 1) || exch[w]?.has(r - 2) || (hitOnQ[w] || []).some((h) => h[1] === r && h[0] < firstQ);
    const campWork = (d.cdmg.length && acts.some((e) => (cdmgQ.get(e.q) || []).some((x) => x[2] === w)));
    const ctx = fight ? 'F' : dE <= 5 ? 'N' : campWork ? 'C' : 'O';
    // channel at turn start
    const cancelled = acts.some((e) => e.k === 'Cancel channel');
    const inChan = chan[w] && !cancelled;
    const stunned = lost.has(w * 4096 + r);
    const usable = c0[5] && !stunned && !inChan;
    // ready at turn start
    const ready = [0, 1].map((s) => (r - lastCast[w][s] >= 8 ? 1 : 0));
    // effects of this turn's events
    const seq = [];
    let atkChamp = false, castAny = false;
    const kit = KIT[type[w]] || [];
    const rs = kit.findIndex((k) => k === 'reset' || k === 'ereset');
    for (const e of acts) {
      if (e.k === 'Move') seq.push('M');
      else if (e.k === 'Attack') {
        const ef = (dmgQ.get(e.q) || []).filter((x) => x[2] === w && x[3] !== w && team[x[3]] !== tm);
        const cf = (cdmgQ.get(e.q) || []).filter((x) => x[2] === w);
        if (ef.length) {
          atkChamp = true;
          const killed = deaths.some((dd) => dd.q === e.q && ef.some((x) => x[3] === dd.who));
          seq.push(killed ? 'K' : 'A');
          for (const x of ef) X.dmg.atkCh += x[4];
        } else seq.push(cf.length ? 'a' : 'x');
        for (const x of cf) X.dmg.atkCamp += x[4];
      } else if (e.k === 'Cast ability') {
        castAny = true;
        const s = e.slot, kind = kit[s] || '?';
        const Y = X.sl[s];
        Y.casts++;
        Y.cctx[ctx]++;
        if (lastCast[w][s] > -100) { Y.wait += Math.max(0, r - lastCast[w][s] - 8); Y.waitN++; }
        const ef = (dmgQ.get(e.q) || []).filter((x) => x[2] === w && x[3] !== w && team[x[3]] !== tm);
        const cf = (cdmgQ.get(e.q) || []).filter((x) => x[2] === w);
        const sf = (stunQ.get(e.q) || []).filter((x) => x[2] === w && team[x[3]] !== tm);
        const hf = (healQ.get(e.q) || []).filter((x) => x[2] === w);
        for (const x of ef) X.dmg.castCh += x[4];
        for (const x of cf) X.dmg.castCamp += x[4];
        let cls;
        if (kind === 'dash' || kind === 'hordash') {
          const from = e.from && !(e.from[0] === 0 && e.from[1] === 0) ? e.from : p0;
          const to = e.to || from;
          const dB = nearestEnemy(S0, tm, from), dA = nearestEnemy(S0, tm, to);
          cls = dB > 8 ? 'travel' : dA < dB ? 'engage' : dA > dB ? 'escape' : 'lateral';
          if (kind === 'hordash') cls = ef.length || sf.length ? 'strike' : (cf.length ? 'campstrike' : cls);
          seq.push('D');
        } else if (kind === 'reset' || kind === 'ereset') { cls = 'reset'; seq.push(s === rs ? 'R' : 'C'); }
        else if (kind === 'shield') {
          cls = 'self'; seq.push('C');
          const tk = (dmgTaken[w] || []).filter((h) => (h[1] === r - 1) || (h[1] === r && h[0] < e.q)).length;
          const after = (dmgTaken[w] || []).filter((h) => h[1] > r && h[1] <= r + 5).length;
          X.shield.n++; if (!tk) X.shield.pre++; if (enemiesWithin(S0, tm, p0, 4).length) X.shield.en4++; if (after) X.shield.hit5++; if (fight) X.shield.fight++;
        } else if (kind === 'heal') {
          cls = hf.length ? 'ally' : 'empty'; seq.push('C');
          for (const x of hf) {
            const tc = st(r - 1, x[3]);
            X.heal.n++; X.heal.miss += tc ? tc[4] - tc[3] : 0; X.heal.frac += tc ? tc[3] / Math.max(1, tc[4]) : 0; if (fight || exch[x[3]]?.has(r - 1) || exch[x[3]]?.has(r)) X.heal.fight++;
          }
        } else {
          cls = ef.length || sf.length ? 'champ' : (cf.length ? 'camp' : 'empty');
          seq.push('C');
        }
        Y.cls[cls] = (Y.cls[cls] || 0) + 1;
        if (type[w] === 'Prism') {
          const bb = bagB(c0[6]);
          X.prism.bag[bb] = (X.prism.bag[bb] || 0) + 1;
          if (ef.length) X.prism.dmgCh[bb] = (X.prism.dmgCh[bb] || [0, 0]).map((v, i) => v + (i ? 1 : ef.reduce((a, x) => a + x[4], 0)));
          if (cf.length) X.prism.dmgCamp[bb] = (X.prism.dmgCamp[bb] || [0, 0]).map((v, i) => v + (i ? 1 : cf.reduce((a, x) => a + x[4], 0)));
        }
        // examples
        const exk = `${type[w]}:${s}:${cls}`;
        if (!X.ex[exk]) X.ex[exk] = r;
        lastCast[w][s] = r;
      } else if (e.k === 'Recall') { seq.push('r'); chan[w] = { k: 'recall', r }; }
      else if (e.k === 'Submit gems') { seq.push('s'); chan[w] = { k: 'trib', r, bag: c0[6] }; }
      else if (e.k === 'Teleport channel') chan[w] = { k: 'tp', r };
      else if (e.k === 'Cancel channel') { if (chan[w] && chan[w].r < r) delete chan[w]; }
      else if (e.k === 'Gems submitted' || e.k === 'Teleport complete') delete chan[w];
    }
    if (usable) {
      X.usable++; X.ctx[ctx]++;
      for (const s of [0, 1]) {
        if (!ready[s]) continue;
        const Y = X.sl[s];
        Y.ready[ctx]++;
        if (acts.some((e) => e.k === 'Cast ability' && e.slot === s)) Y.rcast[ctx]++;
        else if (!castAny) Y.idle[ctx]++;
      }
    }
    if (atkChamp) {
      const sq = seq.join('');
      X.atk.turns++;
      if (rs >= 0 && ready[rs] && usable) { X.atk.ready++; if (sq.includes('R')) X.atk.used++; }
      X.atk.seq[sq] = (X.atk.seq[sq] || 0) + 1;
      const dEnd = nearestEnemy(S1, tm, posOf(c1));
      if (dEnd > dE) X.atk.left++;
      const exk = 'seq:' + sq;
      if (!X.ex[exk]) X.ex[exk] = r;
    }
    // close channels: damage cancels recall, stun / death cancel all, recall completes after 5 turns, tribute after its length
    if (chan[w]) {
      const ch = chan[w];
      const hurt = (dmgTaken[w] || []).some((h) => h[1] === r && (!acts.length || h[0] > acts[acts.length - 1].q));
      if (!c1[5]) delete chan[w];
      else if (ch.k === 'recall' && (hurt || r - ch.r >= 5)) delete chan[w];
      else if (ch.k === 'trib' && r - ch.r >= Math.max(1, Math.ceil((ch.bag || 0) / 10)) + 1) delete chan[w];
      else if (ch.k === 'tp' && r - ch.r >= 4) delete chan[w];
    }
    // Vendetta: champion kill resets cooldowns
    if (type[w] === 'Vendetta' && deaths.some((dd) => dd.r === r && dd.by === w)) lastCast[w] = [-100, -100];
  }
  // stuns applied this round: victim's channel state
  for (const x of (stunR.get(r) || [])) {
    const [q, , a, v] = x;
    if (a < 0 || team[a] === team[v]) continue;
    const X = B[a];
    X.stun.n++;
    // victim channel at that moment: tribute / recall started earlier (this round before q or previous rounds) and still open
    let open = null;
    for (const e of (chanEv[v] || [])) {
      if (e.q >= q) break;
      if (e.r < r - 6) continue;
      if (e.k === 'Recall') open = { k: 'recall', r: e.r }; else if (e.k === 'Submit gems') open = { k: 'trib', r: e.r }; else open = null;
    }
    if (open && open.k === 'recall' && r - open.r > 5) open = null;
    if (open && open.k === 'trib' && r - open.r > 40) open = null;
    const vc = st(r - 1, v);
    const spam = recalls[v] > 0.3 * Math.max(1, aliveN[v]);
    if (open && open.k === 'trib') { X.stun.trib++; X.stun.tribBag += vc ? vc[6] : 0; if (X.stun.ex.length < 6) X.stun.ex.push(['trib', r, v, vc ? vc[6] : 0]); }
    if (open && open.k === 'recall') { if (spam) X.stun.recallSpam = (X.stun.recallSpam || 0) + 1; else { X.stun.recall++; if (X.stun.ex.length < 6) X.stun.ex.push(['recall', r, v, vc ? vc[6] : 0]); } }
    if (deaths.some((dd) => dd.who === v && dd.r >= r && dd.r <= r + 3)) X.stun.kill3++;
  }
}
for (const b of bodies) { B[b.index].recalls = recalls[b.index]; B[b.index].spam = recalls[b.index] > 0.3 * Math.max(1, aliveN[b.index]) ? 1 : 0; }
console.log(JSON.stringify({ file: path.basename(file).replace('.json.gz', ''), final, outcome: d.meta.outcome, bodies: bodies.map((b) => [b.index, b.team, b.type]), B: Object.values(B) }));
