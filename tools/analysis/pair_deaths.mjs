#!/usr/bin/env node
// Cassi & Issac joint deaths in bench.py replays (agent `pair`, session 5).
//
//   node tools/analysis/pair_deaths.mjs [--list] [--maps a,b] [--them] DIR...
//
// "us" = bench BOT_A (NAME_A.repl26a: we are team A, NAME_B.repl26a: team B); --them audits the opponent's pair instead.
// Cassi and Issac die together: when one reaches 0 the other dies in the same step. For every such pair death:
//   trigger   the partner the killer actually hit (the one nearer the killing champion or camp; tie: lower health)
//   other     the partner that died through the link
//   dist      Chebyshev distance between them the round before
//   hp, bag   health fraction and gems carried of each the round before
//   act       what each did in the 3 rounds before (from its own action events):
//             bank (submitting gems), recall, fight (attacked / cast at an enemy champion), farm (attacked / cast at a
//             camp), flee (moved with an enemy within 4 and no attack), walk, idle
//   near      enemies / allies (other than the partner) within 6 of each, the round before
// Summary: pair deaths per game, gems lost per pair death (both bags), share of the C&I body-rounds dead, and the
// split of triggers by activity, distance band, health and bag.
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const LIST = args.includes('--list');
const THEM = args.includes('--them');
const mi = args.indexOf('--maps');
const ONLY = mi >= 0 ? new Set(args[mi + 1].split(',')) : null;
const dirs = args.filter((a, i) => !a.startsWith('--') && !(mi >= 0 && i === mi + 1));
const files = [];
for (const d of dirs) {
  const walk = (p) => {
    if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f));
    else if (p.endsWith('.repl26a')) files.push(p);
  };
  walk(d);
}
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const CI = new Set(['Cassi', 'Issac']);
const T = { games: 0, wins: 0, ci_games: 0, pd: 0, pd_won: 0, pd_lost: 0, gems: 0, deadR: 0, bodyR: 0, solo: 0, otherDeaths: 0, enemyPd: 0 };
const bump = (o, k, v = 1) => (o[k] = (o[k] || 0) + v);
const split = { trig_act: {}, other_act: {}, dist: {}, trig_hp: {}, other_hp: {}, bagger: {}, trig_champ: {}, trig_ne: {}, trig_na: {}, other_ne: {}, by: {}, pair_act: {} };
const rows = [];
for (const f of files.sort()) {
  const base = path.basename(f, '.repl26a');
  const side = base.slice(-1), map = base.slice(0, -2);
  if (ONLY && !ONLY.has(map)) continue;
  const opp = path.basename(path.dirname(f)).replace(/^.*_vs_/, '').replace(/_\d+$/, '');
  let d;
  try { d = await decode(fs.readFileSync(f)); } catch (e) { console.error(`skip ${f}: ${e.message}`); continue; }
  const us = (side === 'A' ? 0 : 1) ^ (THEM ? 1 : 0);
  const R = d.rounds;
  const byR = new Map(R.map((r) => [r.r, r]));
  const fin = R[R.length - 1];
  T.games++;
  const won = fin.sub[us] > fin.sub[1 - us] || (fin.sub[us] === fin.sub[1 - us] && (d.meta.outcome === us + 1));
  T.wins += won;
  const ciIdx = d.meta.bodies.filter((b) => b.team === us && CI.has(b.type)).map((b) => b.index);
  const ciEnemy = d.meta.bodies.filter((b) => b.team !== us && CI.has(b.type)).map((b) => b.index);
  if (ciIdx.length !== 2) continue;
  T.ci_games++;
  for (const r of R) for (const c of r.ch) if (ciIdx.includes(c[0])) { T.bodyR++; if (!c[7]) T.deadR++; }
  const deaths = d.events.filter((e) => e.k === 'Death');
  // enemy pair deaths (for context)
  const ePd = new Set();
  for (const e of deaths) if (ciEnemy.includes(e.who)) ePd.add(e.r);
  T.enemyPd += ePd.size;
  for (const e of deaths) if (e.team === us && !ciIdx.includes(e.who)) T.otherDeaths++;
  const evBy = new Map();
  for (const e of d.events) if (e.who !== undefined && e.team === us) { if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
  const seenRounds = new Set();
  for (const e of deaths) {
    if (e.team !== us || !ciIdx.includes(e.who) || seenRounds.has(e.r)) continue;
    const pair = deaths.filter((o) => o.r === e.r && o.team === us && ciIdx.includes(o.who));
    seenRounds.add(e.r);
    if (pair.length < 2) { T.solo++; continue; }
    T.pd++;
    if (won) T.pd_won++; else T.pd_lost++;
    const prev = byR.get(e.r - 1) || byR.get(e.r);
    const cur = (idx) => prev.ch.find((c) => c[0] === idx);
    const [a, b] = ciIdx.map(cur);
    const pa = [a[3], a[4]], pb = [b[3], b[4]];
    // killer position
    let kpos = null;
    if (e.by === 'camp') { /* camp index unknown in this event: use actor */ }
    if (typeof e.by === 'number') { const k = prev.ch.find((c) => c[0] === e.by); if (k) kpos = [k[3], k[4]]; }
    const campPos = (() => {
      const ev = d.events.find((x) => x.r === e.r && x.k === 'Attack' && x.camp !== undefined && x.to && (cheb(x.to, pa) === 0 || cheb(x.to, pb) === 0));
      return ev ? ev.to : null;
    })();
    let trig;
    const frac = (c) => c[5] / Math.max(1, c[6]);
    if (kpos) trig = cheb(kpos, pa) < cheb(kpos, pb) ? a : cheb(kpos, pb) < cheb(kpos, pa) ? b : (frac(a) <= frac(b) ? a : b);
    else if (campPos) trig = cheb(campPos, pa) === 0 ? a : b;
    else trig = frac(a) <= frac(b) ? a : b;
    const oth = trig === a ? b : a;
    const by = typeof e.by === 'number' ? 'champ' : e.by === 'camp' || e.step === 'Attack' && !kpos ? 'camp' : String(e.step);
    const act = (c) => {
      const L = (evBy.get(c[0]) || []).filter((x) => x.r >= e.r - 3 && x.r <= e.r);
      if (L.some((x) => x.k === 'Submit gems')) return 'bank';
      if (L.some((x) => x.k === 'Recall')) return 'recall';
      let fight = false, farm = false, moved = false;
      for (const x of L) {
        if ((x.k === 'Attack' || x.k === 'Cast ability') && x.to) {
          const snap = byR.get(x.r - 1) || prev;
          const hitChamp = snap.ch.some((q) => q[1] !== us && q[7] && q[3] === x.to[0] && q[4] === x.to[1]);
          if (hitChamp) fight = true; else farm = true;
        }
        if (x.k === 'Move') moved = true;
      }
      if (fight) return 'fight';
      if (farm) return 'farm';
      const ne = prev.ch.filter((q) => q[1] !== us && q[7] && q[3] >= 0 && cheb([q[3], q[4]], [c[3], c[4]]) <= 4).length;
      if (moved && ne) return 'flee';
      if (moved) return 'walk';
      return 'idle';
    };
    const near = (c, team) => prev.ch.filter((q) => q[0] !== c[0] && !ciIdx.includes(q[0]) && q[1] === team && q[7] && q[3] >= 0 && cheb([q[3], q[4]], [c[3], c[4]]) <= 6).length;
    const dist = cheb(pa, pb);
    const ta = act(trig), oa = act(oth);
    const gems = (trig[8] || 0) + (oth[8] || 0);
    T.gems += gems;
    const dband = dist <= 3 ? '0-3' : dist <= 6 ? '4-6' : dist <= 12 ? '7-12' : '13+';
    const hb = (c) => { const x = frac(c); return x < 0.25 ? '<25%' : x < 0.5 ? '25-50%' : x < 0.75 ? '50-75%' : '75%+'; };
    bump(split.trig_act, ta); bump(split.other_act, oa); bump(split.dist, dband); bump(split.trig_hp, hb(trig)); bump(split.other_hp, hb(oth));
    bump(split.bagger, oth[8] > trig[8] ? 'other bag bigger' : trig[8] > oth[8] ? 'trigger bag bigger' : 'equal');
    bump(split.trig_champ, d.meta.bodies[trig[0]].type);
    bump(split.trig_ne, String(Math.min(3, near(trig, 1 - us))) + (near(trig, 1 - us) >= 3 ? '+' : ''));
    bump(split.trig_na, String(Math.min(3, near(trig, us))) + (near(trig, us) >= 3 ? '+' : ''));
    bump(split.other_ne, String(Math.min(3, near(oth, 1 - us))) + (near(oth, 1 - us) >= 3 ? '+' : ''));
    bump(split.by, by);
    bump(split.pair_act, `${ta}/${oa}`);
    rows.push({ map, side, opp, r: e.r, trig: d.meta.bodies[trig[0]].type, ta, oa, dist, th: frac(trig).toFixed(2), oh: frac(oth).toFixed(2), tb: trig[8], ob: oth[8],
      tne: near(trig, 1 - us), tna: near(trig, us), one: near(oth, 1 - us), ona: near(oth, us), by });
  }
}
const pc = (x) => (100 * x).toFixed(1);
console.log(`games ${T.games} (with our C&I ${T.ci_games}), won ${pc(T.wins / Math.max(1, T.games))}%`);
console.log(`pair deaths ${T.pd} = ${(T.pd / Math.max(1, T.ci_games)).toFixed(2)} per game (in won games ${T.pd_won}, lost ${T.pd_lost}); enemy C&I pair deaths ${(T.enemyPd / Math.max(1, T.ci_games)).toFixed(2)} per game`);
console.log(`other bodies' deaths ${(T.otherDeaths / Math.max(1, T.ci_games)).toFixed(2)} per game; unpaired C&I deaths ${T.solo}`);
console.log(`gems lost in pair deaths ${T.gems} = ${(T.gems / Math.max(1, T.pd)).toFixed(1)} per pair death, ${(T.gems / Math.max(1, T.ci_games)).toFixed(1)} per game`);
console.log(`C&I body-rounds dead ${pc(T.deadR / Math.max(1, T.bodyR))}%`);
const show = (name, o) => {
  const tot = Object.values(o).reduce((s, v) => s + v, 0);
  console.log(`${name.padEnd(12)} ` + Object.entries(o).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${k} ${v} (${pc(v / Math.max(1, tot))}%)`).join(', '));
};
for (const [k, v] of Object.entries(split)) if (k !== 'pair_act') show(k, v);
show('pair_act', Object.fromEntries(Object.entries(split.pair_act).sort((x, y) => y[1] - x[1]).slice(0, 12)));
if (LIST) for (const r of rows) console.log(`${r.map.padEnd(16)} ${r.side} ${r.opp.padEnd(5)} r${String(r.r).padEnd(5)} trig ${r.trig.padEnd(5)} ${r.ta.padEnd(6)} hp${r.th} bag${String(r.tb).padEnd(3)} e${r.tne}a${r.tna} | other ${r.oa.padEnd(6)} hp${r.oh} bag${String(r.ob).padEnd(3)} e${r.one}a${r.ona} | dist ${r.dist} by ${r.by}`);
