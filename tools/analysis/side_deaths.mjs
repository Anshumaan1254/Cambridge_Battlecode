#!/usr/bin/env node
// Per-map, per-side death audit of bench.py replays (agent `side`, session 4).
//
//   node tools/analysis/side_deaths.mjs [--maps a,b] [--list] DIR...
//
// "us" = bench BOT_A (NAME_A.repl26a: we are team A, NAME_B.repl26a: team B).
// Per game: result, deaths us-them, opening (kills in rounds <= 150 each way, round of first death and whose),
// and our deaths split by what the body was doing:
//   bag    died carrying >= 20 gems (a bank or farm trip with a bag)
//   alt4   died within 4 tiles of an altar some team banked at in this game
//   far    died nearer the enemy spawn than ours (in their half)
//   alone  no living ally body (C&I partner excluded) within 6 tiles at the round before
//   outn   enemy bodies within 6 outnumber ours (victim included) at the round before
// --list prints every death of ours: round, champ, tile, bag, hp of the round before, nearest ally/enemy.
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const LIST = args.includes('--list');
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
const tot = {};
for (const f of files.sort()) {
  const base = path.basename(f, '.repl26a');
  const side = base.slice(-1), map = base.slice(0, -2);
  if (ONLY && !ONLY.has(map)) continue;
  const opp = path.basename(path.dirname(f)).replace(/^.*_vs_/, '').replace(/_\d+$/, '');
  const d = await decode(fs.readFileSync(f));
  const us = side === 'A' ? 0 : 1;
  const R = d.rounds;
  const spawn = [null, null];
  for (const c of R[0].ch) if (c[7] && !spawn[c[1]]) spawn[c[1]] = [c[3], c[4]];
  for (const r of R.slice(0, 5)) for (const c of r.ch) if (c[7] && !spawn[c[1]]) spawn[c[1]] = [c[3], c[4]];
  const altars = [];
  for (const e of d.events) if (e.k === 'Submit gems' && e.to && !altars.some((a) => a[0] === e.to[0] && a[1] === e.to[1])) altars.push(e.to);
  const byR = new Map(R.map((r) => [r.r, r]));
  const deaths = d.events.filter((e) => e.k === 'Death');
  // Cassi & Issac die together: the primary death is the partner that had less health the round before.
  const hpBefore = (e) => { const p = byR.get(e.r - 1) || byR.get(e.r); const c = p && p.ch.find((x) => x[0] === e.who); return c ? c[5] : 0; };
  const linked = (e) => (e.champ === 'Issac' || e.champ === 'Cassi') && deaths.some((o) => o !== e && o.r === e.r && o.team === e.team && o.champ === (e.champ === 'Issac' ? 'Cassi' : 'Issac') &&
    (hpBefore(o) < hpBefore(e) || (hpBefore(o) === hpBefore(e) && o.who < e.who)));
  const fin = R[R.length - 1];
  const g = { map, side, opp, won: d.meta.outcome === us || d.meta.outcome === ['teamA', 'teamB'][us] || (d.meta.winner !== undefined && d.meta.winner === us), sub: fin.sub, dUs: 0, dThem: 0, open: [0, 0], first: null, bag: 0, alt4: 0, far: 0, alone: 0, outn: 0, list: [] };
  for (const e of deaths) {
    if (linked(e)) { if (e.team === us) g.dUs++; else g.dThem++; continue; }
    if (e.team === us) g.dUs++; else g.dThem++;
    if (e.r <= 150) g.open[e.team === us ? 1 : 0]++;
    if (!g.first) g.first = `${e.team === us ? 'us' : 'them'}@${e.r}`;
    if (e.team !== us) continue;
    const prev = byR.get(e.r - 1) || byR.get(e.r);
    const at = e.at;
    let ally = 99, enemy = 99, nA = 1, nE = 0, hp = -1;
    for (const c of prev.ch) {
      if (!c[7] || c[3] < 0) continue;
      if (c[0] === e.who) { hp = c[5]; continue; }
      const dd = cheb([c[3], c[4]], at);
      const partner = (e.champ === 'Cassi' && d.meta.bodies[c[0]].type === 'Issac') || (e.champ === 'Issac' && d.meta.bodies[c[0]].type === 'Cassi');
      if (c[1] === us) { if (!partner) { ally = Math.min(ally, dd); if (dd <= 6) nA++; } }
      else { enemy = Math.min(enemy, dd); if (dd <= 6) nE++; }
    }
    const bag = e.bag || 0;
    const a4 = altars.some((a) => cheb(a, at) <= 4);
    const far = spawn[1 - us] && cheb(at, spawn[1 - us]) < cheb(at, spawn[us]);
    if (bag >= 20) g.bag++;
    if (a4) g.alt4++;
    if (far) g.far++;
    if (ally > 6) g.alone++;
    if (nE > nA) g.outn++;
    g.list.push(`r${e.r} ${e.champ} @${at} bag${bag} hp${hp} ally${ally} enemy${enemy} ${nA}v${nE}${a4 ? ' ALT' : ''}${far ? ' FAR' : ''} by:${e.step}`);
  }
  const won = fin.sub[us] > fin.sub[1 - us] || (fin.sub[us] === fin.sub[1 - us] && g.won);
  console.log(`${map.padEnd(14)} ${side} ${opp.padEnd(6)} ${won ? 'W' : 'L'} ${String(fin.sub[us]).padStart(4)}-${String(fin.sub[1 - us]).padEnd(4)} r${String(fin.r).padEnd(4)} deaths ${String(g.dUs).padStart(2)}-${String(g.dThem).padEnd(2)} open(k-d) ${g.open[0]}-${g.open[1]} first ${g.first || '-'}  bag${g.bag} alt${g.alt4} far${g.far} alone${g.alone} outn${g.outn}`);
  if (LIST) for (const l of g.list) console.log('     ' + l);
  const k = `${map} ${side}`;
  const t = (tot[k] ||= { n: 0, w: 0, du: 0, dt: 0, bag: 0, alt: 0, far: 0, alone: 0, outn: 0 });
  t.n++; t.w += won; t.du += g.dUs; t.dt += g.dThem; t.bag += g.bag; t.alt += g.alt4; t.far += g.far; t.alone += g.alone; t.outn += g.outn;
}
console.log('\nper map and side: wins/games, deaths us-them per game, our death causes per game');
for (const [k, t] of Object.entries(tot).sort())
  console.log(`${k.padEnd(18)} ${t.w}/${t.n}  deaths ${(t.du / t.n).toFixed(1)}-${(t.dt / t.n).toFixed(1)}  bag ${(t.bag / t.n).toFixed(1)} alt ${(t.alt / t.n).toFixed(1)} far ${(t.far / t.n).toFixed(1)} alone ${(t.alone / t.n).toFixed(1)} outn ${(t.outn / t.n).toFixed(1)}`);
