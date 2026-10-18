#!/usr/bin/env node
// Why our champions die (agent fight7, session 7). Needs XM_TRACE builds of "us" (bench BOT_A): combat() prints
// FC (decision: fight, killable, in reach, can escape, advantage, enemies), FY (dist home, task, recall possible,
// remembered hidden enemies, visible enemies within 12) and DTH (task and dist home at death) lines.
//
//   node tools/analysis/fight_deaths.mjs [--list] [--by-opp] DIR...
//
// One "incident" per primary death (Cassi & Issac: the partner nearer the killer; the linked death counts as a
// second body). The victim's FC lines in the 15 rounds before form the episode (consecutive lines, gaps <= 3):
//   camp        killed by a camp with no enemy champion decision in the last 3 rounds
//   fled        last decision fight=0 (walking away in reach) - split by whether an escapable fight was chosen before
//   cornered    last decision fight=1 with can_escape=0 - split the same way
//   fight_esc   died while still choosing to fight with can_escape=1 (the estimate was wrong at the end)
//   none        no decision line (killed out of the blue / outside the 9-tile view)
// For each: the killer's kit (dash / ranged / melee), dist home, recall possible at the last free decision,
// enemies at the first escapable choice vs the most seen later (arrivals), hidden remembered enemies.
// Also "fight starts": fight=1 with can_escape=1 after >= 4 rounds without a fight decision; outcome within 12
// rounds: our death (this body), enemy deaths within 8 tiles.
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const LIST = args.includes('--list');
const BYOPP = args.includes('--by-opp');
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
const bump = (o, k, v = 1) => (o[k] = (o[k] || 0) + v);
const kv = (l) => Object.fromEntries(l.trim().split(' ').slice(1).map((t) => t.split('=')).map(([k, v]) => [k, isNaN(+v) ? v : +v]));
const KITS = {};
const TOT = {};
const tot = (opp) => (TOT[opp] ||= { games: 0, wins: 0, deaths: 0, bodies: 0, inc: 0, cat: {}, sub: {}, killer: {}, fled_killer: {}, fled_dh: {}, fled_rec: {}, arrive: {}, choice_ne: {},
  choice_rule: {}, hid: {}, champ: {}, starts: 0, start_die: 0, start_kill: 0, starts_ne: {}, start_die_ne: {}, start_kill_ne: {}, eDeaths: 0, fled_task: {}, catChamp: {}, flee_len: {}, fled_dh0: {}, flee_adv: {}, flee_esc: {}, flee_tdie: {}, flee_ally: {}, su: {}, su_die: {}, su_kill: {}, sd: {}, sd_die: {}, sd_kill: {} });
const rows = [];
for (const f of files.sort()) {
  const base = path.basename(f, '.repl26a');
  const side = base.slice(-1), map = base.slice(0, -2);
  const us = side === 'A' ? 0 : 1;
  const opp = path.basename(path.dirname(f)).replace(/^.*_vs_/, '').replace(/_\d+$/, '');
  const raw = fs.readFileSync(f);
  let text = '';
  try { text = unwrapReplay(raw, us ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, ''); } catch { continue; }
  const FC = new Map(), FY = new Map(), DTH = new Map();
  const key = (ty, r) => ty * 10000 + r;
  for (const l of text.split('\n')) {
    if (l.startsWith('FC ')) { const o = kv(l); FC.set(key(o.ty, o.r), o); }
    else if (l.startsWith('FY ')) { const o = kv(l); FY.set(key(o.ty, o.r), o); }
    else if (l.startsWith('DTH ')) { const o = kv(l); DTH.set(key(o.ty, o.r), o); }
    else if (l.startsWith('KIT ')) { const o = kv(l); KITS[o.ty] = o; }
  }
  let d;
  try { d = await decode(raw); } catch (e) { console.error(`skip ${f}: ${e.message}`); continue; }
  const T = tot(opp), A = tot('ALL');
  const R = d.rounds;
  const byR = new Map(R.map((r) => [r.r, r]));
  const fin = R[R.length - 1];
  const won = fin.sub[us] > fin.sub[1 - us] || (fin.sub[us] === fin.sub[1 - us] && d.meta.outcome === us + 1);
  for (const X of [T, A]) X.games++, X.wins += won;
  const typeOf = new Map(d.meta.bodies.map((b) => [b.index, CHAMP.indexOf(b.type)]));
  const deaths = d.events.filter((e) => e.k === 'Death');
  const ours = deaths.filter((e) => e.team === us);
  for (const X of [T, A]) X.deaths += ours.length, X.eDeaths += deaths.length - ours.length;
  // incidents: C&I linked deaths in the same round collapse to one (the trigger)
  const used = new Set();
  for (const e of ours) {
    if (used.has(e)) continue;
    let victim = e;
    const ty = typeOf.get(e.who);
    if (ty === 3 || ty === 4) {
      const mate = ours.find((o) => o !== e && o.r === e.r && (typeOf.get(o.who) === 3 || typeOf.get(o.who) === 4));
      if (mate) {
        used.add(mate);
        const prev = byR.get(e.r - 1) || byR.get(e.r);
        const killer = typeof e.by === 'number' ? prev.ch.find((c) => c[0] === e.by) : null;
        const pick = typeof mate.by === 'number' && typeof e.by !== 'number' ? mate : e;
        victim = pick;
        if (killer) {
          const pa = prev.ch.find((c) => c[0] === e.who), pb = prev.ch.find((c) => c[0] === mate.who);
          victim = cheb([killer[3], killer[4]], [pa[3], pa[4]]) <= cheb([killer[3], killer[4]], [pb[3], pb[4]]) ? e : mate;
          victim = { ...victim, by: e.by };
        }
      }
    }
    used.add(e);
    const vty = typeOf.get(victim.who);
    const bodies = (vty === 3 || vty === 4) && ours.some((o) => o !== e && o.r === e.r && (typeOf.get(o.who) === 3 || typeOf.get(o.who) === 4)) ? 2 : 1;
    // episode
    const ep = [];
    for (let r = victim.r; r >= victim.r - 15; --r) {
      const o = FC.get(key(vty, r));
      if (o) { if (ep.length && ep[0].r - r > 3) break; ep.unshift(o); }
      else if (!ep.length && victim.r - r > 3) break;
    }
    const last = ep[ep.length - 1];
    const killerTy = typeof victim.by === 'number' ? typeOf.get(victim.by) : -1;
    const chosen = ep.find((o) => o.fight === 1 && o.esc === 1);
    let cat;
    const chan = d.events.some((x) => x.who === victim.who && x.r >= victim.r - 6 && x.r <= victim.r && (x.k === 'Recall' || x.k === 'Submit gems' || x.k === 'Consumable'));
    if (victim.by === 'camp' && (!last || victim.r - last.r > 3)) cat = 'camp';
    else if ((!last || victim.r - last.r > 3) && chan) cat = 'channel';
    else if (!last || victim.r - last.r > 3) cat = 'none';
    else if (last.fight === 0) cat = chosen ? 'fled_after_choice' : 'fled';
    else if (last.esc === 0) cat = chosen ? 'cornered_after_choice' : 'cornered';
    else cat = 'fight_esc';
    const fy = (o) => (o ? FY.get(key(vty, o.r)) : null);
    const dth = last ? FY.get(key(vty, last.r)) : null;
    const maxNe = ep.reduce((m, o) => Math.max(m, o.ne), 0);
    const maxNe12 = ep.reduce((m, o) => Math.max(m, fy(o)?.ne12 ?? 0), 0);
    const kit = KITS[killerTy];
    const kk = killerTy < 0 ? 'camp' : !kit ? CHAMP[killerTy] : `${CHAMP[killerTy]}(${kit.dash ? 'dash' : kit.ranged ? 'ranged' : 'melee'})`;
    for (const X of [T, A]) {
      X.inc++; X.bodies += bodies;
      bump(X.cat, cat, bodies);
      bump(X.killer, kk, bodies);
      bump(X.champ, CHAMP[vty], bodies);
      bump(X.catChamp, `${CHAMP[vty]}:${cat.split('_')[0]}`, bodies);
      if (cat.startsWith('fled')) {
        bump(X.fled_killer, kk, bodies);
        // the flee: trailing fight=0 decisions; dist home at its start and at death
        let k = ep.length - 1;
        while (k > 0 && ep[k - 1].fight === 0) --k;
        const f0 = fy(ep[k]);
        const dh0 = f0?.dh ?? -1, dhe = dth?.dh ?? -1;
        const band = (x) => (x < 0 ? '?' : x <= 3 ? '0-3' : x <= 7 ? '4-7' : x <= 12 ? '8-12' : x <= 20 ? '13-20' : '21+');
        bump(X.fled_dh0, band(dh0), bodies);
        bump(X.fled_dh, band(dhe), bodies);
        bump(X.flee_len, String(Math.min(6, ep.length - k)), bodies);
        bump(X.fled_task, String(f0?.task ?? '?'), bodies);
        const anyRec = ep.slice(k).some((o) => fy(o)?.rec === 1);
        const e0 = ep[k];
        bump(X.flee_adv, e0.adv < 0.634 ? '<0.63' : e0.adv < 0.873 ? '0.63-0.87' : e0.adv < 1.3 ? '0.87-1.3' : '1.3+', bodies);
        bump(X.flee_esc, `esc${e0.esc} reach${e0.reach}`, bodies);
        {
          const sn = byR.get(e0.r);
          const me = sn && sn.ch.find((q) => q[0] === victim.who);
          let best = 99;
          if (me) for (const q of sn.ch) if (q[1] === us && q[7] && q[0] !== victim.who && q[5] > 0.5 * q[6] && !((vty === 3 || vty === 4) && (q[2] === 3 || q[2] === 4))) best = Math.min(best, cheb([q[3], q[4]], [me[3], me[4]]));
          bump(X.flee_ally, best <= 4 ? 'ally<=4' : best <= 8 ? 'ally5-8' : best <= 12 ? 'ally9-12' : 'none<=12', bodies);
        }
        bump(X.flee_tdie, e0.tdie < dh0 ? 'tdie<dh' : e0.tdie < 2 * dh0 ? 'dh<=tdie<2dh' : 'tdie>=2dh', bodies);
        bump(X.fled_rec, anyRec ? 'recall was possible' : 'no', bodies);
      }
      if (chosen) {
        const ne1 = chosen.ne;
        bump(X.choice_ne, `${ne1}v${chosen.na + 1}`, bodies);
        bump(X.arrive, maxNe > ne1 ? `+${Math.min(3, maxNe - ne1)}` : '0', bodies);
        const rule = chosen.kill ? 'killable' : chosen.reach ? 'fight_back' : 'margin';
        bump(X.choice_rule, `${rule}${chosen.iso ? '/iso' : ''}`, bodies);
        bump(X.hid, (fy(chosen)?.hid ?? 0) > 0 ? 'hidden remembered' : 'none hidden', bodies);
      }
    }
    rows.push({ opp, map, side, r: victim.r, champ: CHAMP[vty], bodies, cat, kk, ep: ep.length, chosen: chosen ? `adv${chosen.adv.toFixed(2)} ne${chosen.ne} na${chosen.na} hp${(chosen.hp / chosen.mhp).toFixed(2)} kill${chosen.kill} reach${chosen.reach}` : '', maxNe, maxNe12,
      dh: dth?.dh, task: dth?.task, gems: victim.bag });
  }
  // fight starts
  const enemyDeaths = deaths.filter((x) => x.team !== us);
  for (const vt of new Set([...FC.values()].map((o) => o.ty))) {
    const lines = [...FC.values()].filter((o) => o.ty === vt).sort((a, b) => a.r - b.r);
    let lastFight = -100;
    const myIdx = d.meta.bodies.filter((b) => b.team === us && CHAMP.indexOf(b.type) === vt).map((b) => b.index);
    for (const o of lines) {
      if (o.fight === 1 && o.esc === 1 && !o.reach && o.r - lastFight >= 4) {
        const die = ours.some((x) => myIdx.includes(x.who) && x.r > o.r && x.r <= o.r + 12);
        const kills = enemyDeaths.filter((x) => x.r >= o.r && x.r <= o.r + 12 && cheb(x.at, [o.x, o.y]) <= 8).length;
        const nb = `${Math.min(3, o.ne)}v${Math.min(3, o.na + 1)}`;
        const fyo = FY.get(key(vt, o.r));
        const snap = byR.get(o.r);
        const alive = snap ? snap.ch.filter((q) => q[1] !== us && q[7]).length : 0;
        const unk = fyo ? Math.max(0, alive - fyo.ne12 - fyo.hid) : -1;
        const dhb = !fyo ? '?' : fyo.dh <= 7 ? 'dh0-7' : fyo.dh <= 14 ? 'dh8-14' : fyo.dh <= 21 ? 'dh15-21' : 'dh22+';
        for (const X of [T, A]) {
          bump(X.su, `unk${Math.min(4, unk)}`); bump(X.su_die, `unk${Math.min(4, unk)}`, die ? 1 : 0); bump(X.su_kill, `unk${Math.min(4, unk)}`, kills);
          bump(X.sd, dhb); bump(X.sd_die, dhb, die ? 1 : 0); bump(X.sd_kill, dhb, kills);
        }
        for (const X of [T, A]) {
          X.starts++; X.start_die += die; X.start_kill += kills;
          bump(X.starts_ne, nb); bump(X.start_die_ne, nb, die ? 1 : 0); bump(X.start_kill_ne, nb, kills);
        }
      }
      if (o.fight === 1) lastFight = o.r;
    }
  }
}
const pc = (x, n) => `${(100 * x / Math.max(1, n)).toFixed(1)}%`;
const show = (name, o, n) => console.log(`  ${name.padEnd(13)} ` + Object.entries(o).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${k} ${v} (${pc(v, n)})`).join(', '));
for (const [opp, X] of Object.entries(TOT)) {
  if (!BYOPP && opp !== 'ALL') continue;
  console.log(`== ${opp}: games ${X.games}, won ${pc(X.wins, X.games)}, our body deaths ${(X.deaths / X.games).toFixed(2)}/game vs theirs ${(X.eDeaths / X.games).toFixed(2)}; incidents ${X.inc}`);
  show('category', X.cat, X.bodies);
  show('victim', X.champ, X.bodies);
  show('killer', X.killer, X.bodies);
  const fl = Object.entries(X.cat).filter(([k]) => k.startsWith('fled')).reduce((s, [, v]) => s + v, 0);
  console.log(`  fled deaths ${fl}:`);
  show(' fled killer', X.fled_killer, fl);
  show(' dh flee start', X.fled_dh0, fl);
  show(' dh at death', X.fled_dh, fl);
  show(' flee rounds', X.flee_len, fl);
  show(' task before', X.fled_task, fl);
  show(' recall', X.fled_rec, fl);
  show(' adv at flee', X.flee_adv, fl);
  show(' esc at flee', X.flee_esc, fl);
  show(' tdie vs dh', X.flee_tdie, fl);
  show(' healthy ally', X.flee_ally, fl);
  const ch = Object.values(X.choice_ne).reduce((s, v) => s + v, 0);
  console.log(`  deaths after an escapable fight choice ${ch}:`);
  show(' ne v us', X.choice_ne, ch);
  show(' arrivals', X.arrive, ch);
  show(' rule', X.choice_rule, ch);
  show(' memory', X.hid, ch);
  console.log(`  fight starts (escapable, not in reach) ${X.starts}: this body died within 12 ${pc(X.start_die, X.starts)}, enemy deaths within 12 rounds/8 tiles ${(X.start_kill / Math.max(1, X.starts)).toFixed(2)} per start`);
  for (const [k, n] of Object.entries(X.starts_ne).sort((a, b) => b[1] - a[1]).slice(0, 10))
    console.log(`    ${k.padEnd(5)} n=${String(n).padEnd(5)} died ${pc(X.start_die_ne[k] || 0, n).padEnd(6)} kills/start ${((X.start_kill_ne[k] || 0) / n).toFixed(2)}`);
  for (const [a, b, c] of [[X.su, X.su_die, X.su_kill], [X.sd, X.sd_die, X.sd_kill]])
    for (const [k, n] of Object.entries(a).sort())
      console.log(`    ${k.padEnd(8)} n=${String(n).padEnd(5)} died ${pc(b[k] || 0, n).padEnd(6)} kills/start ${((c[k] || 0) / n).toFixed(2)}`);
}
if (LIST) for (const r of rows) console.log(`${r.opp.padEnd(6)} ${r.map.padEnd(18)} ${r.side} r${String(r.r).padEnd(5)} ${r.champ.padEnd(8)} x${r.bodies} ${r.cat.padEnd(22)} by ${String(r.kk).padEnd(16)} ep${r.ep} maxNe${r.maxNe}/${r.maxNe12} dh${r.dh} task${r.task} bag${r.gems} ${r.chosen}`);
