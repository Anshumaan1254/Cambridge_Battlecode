// usage: node tools/analysis/econ_open.mjs [--both] REPLAY...   (bench naming: *_A.repl26a = our bot is team A, *_B = team B)
// Economy of the opening and of the whole game, per body (the report's metrics, HOUSEOFCODERS report §12.6):
// first capture, gold earned / camp gems at r100 / r200, first emblem round (5 shards of a family), captures that
// were split with an ally (same round, same group), rounds dead, and the longest stretch alive without earning
// anything (gems or gold) and without a tribute: the "pilgrimage Ren" watchdog.
// --both also prints the opponent team.
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const both = args.includes('--both');
const files = args.filter((a) => !a.startsWith('--'));
const tot = {};
for (const f of files) {
  const our = /_B\.repl26a$/.test(f) ? 1 : 0;
  const d = await decode(unwrapReplay(fs.readFileSync(f)), { every: 1 });
  const teams = both ? [our, 1 - our] : [our];
  console.log(`== ${f.split('/').pop()}  final r${d.meta.finalRound}  banked ${d.meta.submitted ? d.meta.submitted.join('-') : '?'}  (our team ${our})`);
  for (const team of teams) {
    const bodies = d.meta.bodies.filter((b) => b.team === team);
    const caps = d.events.filter((e) => e.team === team && e.k === 'CaptureGems');
    const byRound = {};
    for (const c of caps) (byRound[c.r + ':' + c.gems] ||= []).push(c.who);
    for (const b of bodies) {
      const st = { firstCap: null, g100: 0, g200: 0, gold100: 0, gold200: 0, gems: 0, gold: 0, emblem: null, split: 0, caps: 0, dead: 0, idle: 0, idleFrom: 0 };
      let prev = null, lastEarn = 0, alive0 = 0;
      for (const r of d.rounds) {
        const c = r.ch.find((q) => q[0] === b.index);
        if (!c) continue;
        const [, , , , , , , alive, gems, gold, , items] = c;
        if (!alive) { st.dead++; lastEarn = r.r; prev = c; continue; }
        if (prev) {
          const dg = gold - prev[9];
          if (dg > 0) { st.gold += dg; lastEarn = r.r; }
          if (gems < prev[8] && prev[7]) lastEarn = r.r; // banked
        }
        if (r.r - lastEarn > st.idle) { st.idle = r.r - lastEarn; st.idleFrom = lastEarn; }
        if (st.emblem === null && items) {
          // items: [[itemIndex, count]]: an emblem is a family with 5 shards (count >= 5 of one index)
          for (const [, q] of items) if (q >= 5) { st.emblem = r.r; break; }
        }
        if (r.r === 100) { st.gold100 = st.gold; }
        if (r.r === 200) { st.gold200 = st.gold; }
        prev = c;
      }
      for (const c of caps.filter((q) => q.who === b.index)) {
        st.caps++; st.gems += c.gems;
        if (st.firstCap === null) st.firstCap = c.r;
        if (c.r <= 100) st.g100 += c.gems;
        if (c.r <= 200) st.g200 += c.gems;
        if (byRound[c.r + ':' + c.gems].length > 1) st.split++;
      }
      const name = CHAMP.indexOf(b.type) >= 0 ? b.type : b.type;
      console.log(`  ${team === our ? 'us ' : 'opp'} ${name.padEnd(8)} firstCap r${String(st.firstCap ?? '-').padEnd(4)} gems@100 ${String(st.g100).padStart(4)} @200 ${String(st.g200).padStart(4)} all ${String(st.gems).padStart(4)}  gold@100 ${String(st.gold100).padStart(4)} @200 ${String(st.gold200).padStart(4)} all ${String(st.gold).padStart(5)}  emblem r${String(st.emblem ?? '-').padEnd(4)} caps ${st.caps} split ${st.split}  dead ${st.dead}  idle ${st.idle} (from r${st.idleFrom})`);
      const k = (team === our ? 'us ' : 'opp') + name;
      const t = (tot[k] ||= { n: 0, firstCap: 0, g100: 0, g200: 0, gems: 0, gold100: 0, gold200: 0, gold: 0, emblem: 0, split: 0, caps: 0, dead: 0, idle: 0 });
      t.n++; for (const key of ['g100', 'g200', 'gems', 'gold100', 'gold200', 'gold', 'split', 'caps', 'dead', 'idle']) t[key] += st[key];
      t.firstCap += st.firstCap ?? d.meta.finalRound; t.emblem += st.emblem ?? d.meta.finalRound;
    }
  }
}
if (files.length > 1) {
  console.log('== means');
  for (const [k, t] of Object.entries(tot)) {
    const m = (x) => (t[x] / t.n).toFixed(0);
    console.log(`  ${k.padEnd(12)} n ${t.n} firstCap ${m('firstCap')} gems@100 ${m('g100')} @200 ${m('g200')} all ${m('gems')} gold@100 ${m('gold100')} @200 ${m('gold200')} all ${m('gold')} emblem ${m('emblem')} caps ${m('caps')} split ${m('split')} dead ${m('dead')} idle ${m('idle')}`);
  }
}
