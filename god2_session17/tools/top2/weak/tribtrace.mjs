#!/usr/bin/env node
// Trace tribute channels with big bags in a fightdump dump (an_weak): for every 'Submit gems' with bag >= MIN by team T (or both), print
// the body's events until the channel ends (done / cancel / stun / lock / death), what the body did right after a self-cancel
// (next 3 actions), enemies within 6 at start / end with their types and hp, damage taken, and altar locks near.
//   node tools/top2/weak/tribtrace.mjs dump.json.gz MIN [TEAM]
import fs from 'node:fs';
import zlib from 'node:zlib';
const [file, MIN, TEAM] = [process.argv[2], +(process.argv[3] || 100), process.argv[4] === undefined ? null : +process.argv[4]];
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const teamOf = (i) => d.meta.bodies[i]?.team, tyOf = (i) => (d.meta.bodies[i]?.type || '').replace('VesperVale', 'Vesper').replace('HeartOfRuin', 'HoR');
const PM = new Map(); for (const e of d.R) { const m = new Map(); for (const c of e[3]) m.set(c[0], c); PM.set(e[0], m); }
const cheb = (a, b, c, e) => Math.max(Math.abs(a - c), Math.abs(b - e));
const evBy = new Map(); for (const e of d.ev) { if (e.who === undefined) continue; if (!evBy.has(e.who)) evBy.set(e.who, []); evBy.get(e.who).push(e); }
const near = (r, b, R = 6) => { const m = PM.get(r); if (!m) return ''; const me = m.get(b); if (!me || !me[5]) return '(dead)'; const out = []; for (const c of m.values()) if (c[5] && c[0] !== b && cheb(c[1], c[2], me[1], me[2]) <= R) out.push(`${teamOf(c[0]) === teamOf(b) ? '+' : '-'}${tyOf(c[0])}@${cheb(c[1], c[2], me[1], me[2])}:${c[3]}/${c[4]}${c[6] ? ' g' + c[6] : ''}`); return out.join(' '); };
console.log(`${file.split(/[\\/]/).pop()} final r${d.meta.finalRound} submitted ${d.meta.submitted}`);
for (const e of d.ev) {
  if (e.k !== 'Submit gems') continue;
  const b = e.who, t = teamOf(b); if (TEAM !== null && t !== TEAM) continue;
  const c0 = PM.get(e.r)?.get(b); const bag = c0 ? c0[6] : 0; if (bag < MIN) continue;
  const list = (evBy.get(b) || []).filter((x) => x.q > e.q);
  let end = null; for (const x of list) { if (x.k !== 'Banked') { end = x; break; } }
  const dmg = d.dmg.filter((x) => x[3] === b && x[0] > e.q && (!end || x[0] <= end.q));
  const dsum = dmg.reduce((a, x) => a + x[4], 0); const dsrc = [...new Set(dmg.map((x) => (x[2] >= 0 ? tyOf(x[2]) : 'camp')))].join(',');
  const stun = d.stun.filter((x) => x[3] === b && x[0] > e.q && (!end || x[0] <= end.q)).map((x) => (x[2] >= 0 ? tyOf(x[2]) : 'camp') + '@r' + x[1]);
  const locks = d.ev.filter((x) => x.k === 'Place altar lock' && x.q > e.q && (!end || x.q <= end.q) && cheb(x.to[0], x.to[1], e.to[0], e.to[1]) <= 1).map((x) => `${teamOf(x.who) === t ? 'own' : 'ENEMY'} lock r${x.r}`);
  const after = end && end.k === 'Cancel channel' ? list.filter((x) => x.q > end.q && x.k !== 'Cancel channel').slice(0, 3).map((x) => `${x.k}@r${x.r}${x.to ? '->' + x.to : ''}`).join(', ') : '';
  console.log(`T${t} ${tyOf(b)}#${b} r${e.r} bag ${bag} need ${Math.ceil(bag / 10)} altar ${e.to} -> ${end ? end.k + ' r' + end.r + ' (+' + (end.r - e.r) + ')' : 'none'} | dmg ${dsum} from ${dsrc || '-'} | stun ${stun.join(',') || '-'} | ${locks.join(',') || 'no lock'}`);
  console.log(`    start near: ${near(e.r, b)}`);
  if (end) console.log(`    end near:   ${near(end.r, b)}${after ? ' | then: ' + after : ''}`);
}
