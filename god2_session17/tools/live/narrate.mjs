#!/usr/bin/env node
// One game as a readable timeline, both teams side by side, every K rounds (default 100):
//   banked gems | captures (count, gems, where: O own half / M middle / T their half) | deaths (where, killer) | max-health sum | gold
//   | our bodies' time split (farm / fight / walk / idle / dead) and theirs.
// Then every death with context (victim, killer, place, bag, nearby allies / enemies) and the first kill / first capture.
//   CAMBC_CACHE=... node tools/live/narrate.mjs replay OUR_TEAM(0|1) [K]
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const [file, US, K] = [process.argv[2], +process.argv[3], +(process.argv[4] || 100)];
const d = await decode(fs.readFileSync(file));
const TH = 1 - US;
const camps = new Set((d.meta.camps || []).map((c) => c.x * 1000 + c.y));
const s1 = d.rounds[1];
const spawn = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
const zone = (team, x, y) => { // relative to `team`: O own half, M middle band, T their half
  const da = Math.max(Math.abs(x - spawn[team][0]), Math.abs(y - spawn[team][1]));
  const db = Math.max(Math.abs(x - spawn[1 - team][0]), Math.abs(y - spawn[1 - team][1]));
  return Math.abs(da - db) <= 4 ? 'M' : da < db ? 'O' : 'T';
};
const nm = (i) => d.meta.bodies[i].type.replace('VesperVale', 'Vesper').replace('HeartOfRuin', 'HoR');
const final = d.meta.finalRound;
const outcome = d.meta.outcome === (US === 0 ? 1 : 2) ? 'WIN' : 'LOSS';
console.log(`${file.split(/[\\/]/).pop()}  ${d.meta.width}x${d.meta.height}  ${outcome} at r${final}  banked ${d.meta.submitted ? d.meta.submitted[US] + '-' + d.meta.submitted[TH] : ''}`);
console.log(`  drafts: us ${d.meta.drafts[US].join(',')} | them ${d.meta.drafts[TH].join(',')}`);
// activity per body-round
const act = new Map();
for (const e of d.events) {
  if ((e.k !== 'Attack' && e.k !== 'Cast ability') || e.who === undefined || !e.to) continue;
  const key = e.who * 100000 + e.r;
  if (camps.has(e.to[0] * 1000 + e.to[1])) { if (!act.has(key)) act.set(key, 'farm'); }
  else act.set(key, 'fight');
}
const caps = d.events.filter((e) => e.k === 'CaptureGems');
const deaths = d.events.filter((e) => e.k === 'Death');
const banks = d.events.filter((e) => e.k === 'Banked');
console.log(`  ${'rounds'.padEnd(9)} | ${'banked'.padEnd(9)} | ${'caps us (O/M/T) gems'.padEnd(22)} | ${'caps them'.padEnd(18)} | ${'deaths us/them'.padEnd(14)} | ${'maxHP us-them'.padEnd(13)} | gold us-them | us farm/fight/walk/idle/dead % | them`);
for (let r0 = 0; r0 < final; r0 += K) {
  const r1 = Math.min(final, r0 + K);
  const s = d.rounds[Math.min(r1, d.rounds.length - 1)];
  const cz = (t) => {
    const cs = caps.filter((e) => e.team === t && e.r > r0 && e.r <= r1);
    const z = { O: 0, M: 0, T: 0 };
    for (const e of cs) z[zone(t, e.at[0], e.at[1])]++;
    return `${cs.length} (${z.O}/${z.M}/${z.T}) ${cs.reduce((a, e) => a + e.gems, 0)}g`;
  };
  const dz = (t) => deaths.filter((e) => e.team === t && e.r > r0 && e.r <= r1).length;
  const hp = (t) => s.ch.filter((c) => c[1] === t).reduce((a, c) => a + c[6], 0);
  const gd = (t) => s.ch.filter((c) => c[1] === t).reduce((a, c) => a + c[9], 0);
  const split = (t) => {
    const n = { farm: 0, fight: 0, walk: 0, idle: 0, dead: 0 };
    for (let r = r0 + 1; r <= r1 && r < d.rounds.length; r++) {
      const ss = d.rounds[r], pp = d.rounds[r - 1];
      if (!ss || !pp) continue;
      for (const c of ss.ch) {
        if (c[1] !== t) continue;
        if (!c[7]) { n.dead++; continue; }
        const a = act.get(c[0] * 100000 + r);
        if (a) { n[a]++; continue; }
        const o = pp.ch.find((q) => q[0] === c[0]);
        n[o && (o[3] !== c[3] || o[4] !== c[4]) ? 'walk' : 'idle']++;
      }
    }
    const tot = Object.values(n).reduce((a, b) => a + b, 0) || 1;
    return ['farm', 'fight', 'walk', 'idle', 'dead'].map((k) => String(Math.round(100 * n[k] / tot)).padStart(2)).join('/');
  };
  console.log(`  ${(r0 + '-' + r1).padEnd(9)} | ${(s.sub[US] + '-' + s.sub[TH]).padEnd(9)} | ${cz(US).padEnd(22)} | ${cz(TH).padEnd(18)} | ${(dz(US) + '/' + dz(TH)).padEnd(14)} | ${(hp(US) + '-' + hp(TH)).padEnd(13)} | ${(gd(US) + '-' + gd(TH)).padEnd(12)} | ${split(US).padEnd(30)} | ${split(TH)}`);
}
// deaths with context
console.log('  deaths (round, victim, team, zone for the victim, killer, bag, allies / enemies within 8 of the victim):');
for (const e of deaths) {
  const s = d.rounds[Math.max(0, e.r - 1)];
  const v = s.ch.find((c) => c[0] === e.who);
  if (!v) continue;
  const near = (team) => s.ch.filter((c) => c[7] && c[1] === team && c[0] !== e.who && Math.max(Math.abs(c[3] - v[3]), Math.abs(c[4] - v[4])) <= 8).length;
  const killer = typeof e.by === 'number' ? nm(e.by) : e.by;
  console.log(`    r${e.r} ${e.team === US ? 'US  ' : 'THEM'} ${nm(e.who).padEnd(9)} ${zone(e.team, v[3], v[4])} by ${String(killer).padEnd(9)} bag ${String(e.bag || 0).padStart(4)}  allies ${near(e.team)} enemies ${near(1 - e.team)}`);
}
const fk = deaths.find((e) => typeof e.by === 'number');
console.log(`  first kill: ${fk ? `r${fk.r} by ${fk.team === US ? 'THEM' : 'US'}` : 'none'};  first capture: us r${caps.find((e) => e.team === US)?.r ?? '-'}, them r${caps.find((e) => e.team === TH)?.r ?? '-'};  banks: us ${banks.filter((e) => e.team === US).length} (${banks.filter((e) => e.team === US).reduce((a, e) => a + e.gems, 0)}g), them ${banks.filter((e) => e.team === TH).length} (${banks.filter((e) => e.team === TH).reduce((a, e) => a + e.gems, 0)}g)`);
