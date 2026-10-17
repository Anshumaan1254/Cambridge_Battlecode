#!/usr/bin/env node
// The fight decisions that led to Cassi & Issac pair deaths (agent `pair`, session 5). Needs XM_TRACE builds
// (combat() prints one FC line per evaluation: hp, advantage, fight, in reach, can escape, ...).
//
//   node tools/analysis/pair_trace.mjs [--list] DIR...
//
// "us" = bench BOT_A. For each pair death of ours: the trigger (partner nearer the killer) and its FC lines over the
// 12 rounds before. Classifies the episode:
//   entry      health fraction at the first FC line in the window (enemy within 9 first seen)
//   chose      a fight decision while we could still escape (fight=1, esc=1): which rule (kill / margin / fight-back)
//   cornered   fight decisions with esc=0
//   fled       fight=0 while in reach (walked away and got caught)
//   last_free  health at the last decision where we could escape
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const LIST = args.includes('--list');
const dirs = args.filter((a) => !a.startsWith('--'));
const files = [];
for (const d of dirs) {
  const walk = (p) => {
    if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f));
    else if (p.endsWith('.repl26a')) files.push(p);
  };
  walk(d);
}
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const TY = { Cassi: 3, Issac: 4 };
const S = { pd: 0, traced: 0, entry: {}, chose: 0, chose_lowhp: 0, chose_kind: {}, cornered: 0, fled: 0, last_free: {}, only_cornered: 0, never_free: 0, lowfree: 0, ne_at_choice: {} };
const bump = (o, k) => (o[k] = (o[k] || 0) + 1);
const band = (x) => (x < 0.25 ? '<25' : x < 0.4 ? '25-40' : x < 0.55 ? '40-55' : x < 0.7 ? '55-70' : '70+');
for (const f of files.sort()) {
  const base = path.basename(f, '.repl26a');
  const side = base.slice(-1), map = base.slice(0, -2);
  const us = side === 'A' ? 0 : 1;
  const raw = fs.readFileSync(f);
  let text = '';
  try { text = unwrapReplay(raw, us ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, ''); } catch { continue; }
  const fc = { 3: new Map(), 4: new Map() };
  for (const l of text.split('\n')) {
    if (!l.startsWith('FC ')) continue;
    const kv = Object.fromEntries(l.slice(3).trim().split(' ').map((t) => t.split('=')));
    const ty = +kv.ty;
    if (ty !== 3 && ty !== 4) continue;
    fc[ty].set(+kv.r, kv);
  }
  const d = await decode(unwrapReplay(raw));
  const ci = d.meta.bodies.filter((b) => b.team === us && (b.type === 'Cassi' || b.type === 'Issac'));
  if (ci.length !== 2) continue;
  const byR = new Map(d.rounds.map((r) => [r.r, r]));
  const deaths = d.events.filter((e) => e.k === 'Death' && e.team === us && ci.some((b) => b.index === e.who));
  const done = new Set();
  for (const e of deaths) {
    if (done.has(e.r)) continue;
    done.add(e.r);
    if (deaths.filter((o) => o.r === e.r).length < 2) continue;
    S.pd++;
    const prev = byR.get(e.r - 1) || byR.get(e.r);
    const cs = ci.map((b) => prev.ch.find((c) => c[0] === b.index));
    let kpos = null;
    if (typeof e.by === 'number') { const k = prev.ch.find((c) => c[0] === e.by); if (k) kpos = [k[3], k[4]]; }
    const fr = (c) => c[5] / Math.max(1, c[6]);
    let ti;
    if (kpos) { const da = cheb(kpos, [cs[0][3], cs[0][4]]), db = cheb(kpos, [cs[1][3], cs[1][4]]); ti = da < db ? 0 : db < da ? 1 : fr(cs[0]) <= fr(cs[1]) ? 0 : 1; }
    else ti = fr(cs[0]) <= fr(cs[1]) ? 0 : 1;
    const tname = ci[ti].type;
    const L = [];
    for (let r = e.r - 12; r < e.r; ++r) { const x = fc[TY[tname]].get(r); if (x) L.push(x); }
    if (!L.length) continue;
    S.traced++;
    const h = (x) => +x.hp / Math.max(1, +x.mhp);
    bump(S.entry, band(h(L[0])));
    const choice = L.find((x) => x.fight === '1' && x.esc === '1');
    if (choice) {
      S.chose++;
      if (h(choice) < 0.5) S.chose_lowhp++;
      const kind = choice.kill === '1' ? 'killable' : +choice.adv >= +choice.fm ? 'margin' : choice.reach === '1' ? 'fight-back' : 'other';
      bump(S.chose_kind, kind);
      bump(S.ne_at_choice, `${choice.ne}v${+choice.na + 1}`);
    }
    if (L.some((x) => x.fight === '1' && x.esc === '0')) S.cornered++;
    if (L.some((x) => x.fight === '0' && x.reach === '1')) S.fled++;
    const free = [...L].reverse().find((x) => x.esc === '1');
    if (free) { bump(S.last_free, band(h(free))); if (h(free) < 0.4) S.lowfree++; } else S.never_free++;
    if (!choice && L.some((x) => x.esc === '0')) S.only_cornered++;
    if (LIST) {
      console.log(`${map} ${side} r${e.r} trig ${tname}`);
      for (const x of L) console.log(`   r${x.r} hp ${h(x).toFixed(2)} adv ${(+x.adv).toFixed(2)} fm ${x.fm} fight ${x.fight} kill ${x.kill} reach ${x.reach} esc ${x.esc} iso ${x.iso} ne ${x.ne} na ${x.na} bk ${x.bk} inc ${x.inc} tdie ${x.tdie}`);
    }
  }
}
const pc = (x) => (100 * x / Math.max(1, S.traced)).toFixed(1) + '%';
console.log(`pair deaths ${S.pd}, with trigger FC lines in the 12 rounds before: ${S.traced}`);
console.log('entry health (first sighting in window):', JSON.stringify(S.entry));
console.log(`chose a fight while escapable: ${S.chose} (${pc(S.chose)}), at <50% health: ${S.chose_lowhp}; by rule ${JSON.stringify(S.chose_kind)}; numbers (enemies v us) ${JSON.stringify(S.ne_at_choice)}`);
console.log(`cornered fights: ${S.cornered} (${pc(S.cornered)}); only cornered, never chose: ${S.only_cornered}; fled in reach: ${S.fled} (${pc(S.fled)})`);
console.log(`health at the last escapable decision: ${JSON.stringify(S.last_free)}; below 40%: ${S.lowfree}; never escapable in window: ${S.never_free}`);
