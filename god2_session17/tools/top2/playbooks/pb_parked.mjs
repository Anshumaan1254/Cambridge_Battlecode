#!/usr/bin/env node
// Parked bodies: runs of >= 60 rounds in which a living body stays within 1 tile of where the run started, off its own spawn, without a
// capture or a bank (attacks / casts allowed: a body poking a camp it cannot kill is parked too). Per team: runs, rounds, the longest run
// (type, start round, tile, gems carried). One JSON line per game.   node tools/top2/playbooks/pb_parked.mjs dump.json.gz...
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const cheb = (a, b, c, d) => Math.max(Math.abs(a - c), Math.abs(b - d));
for (const f of process.argv.slice(2)) {
  try {
    const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
    const bodies = d.meta.bodies, final = d.meta.finalRound;
    const teamOf = (i) => bodies[i].team;
    const sp0 = d.R[0][3];
    const spc = [0, 1].map((t) => { const b = sp0.filter((c) => teamOf(c[0]) === t); return [b.reduce((a, c) => a + c[1], 0) / b.length, b.reduce((a, c) => a + c[2], 0) / b.length]; });
    const S = new Array(final + 1);
    for (let k = 1; k < d.R.length; k++) S[d.R[k][0]] = d.R[k];
    for (let r = 1; r <= final; r++) if (!S[r]) S[r] = S[r - 1];
    const cap = new Set(d.ev.filter((e) => e.k === 'CaptureGems' || e.k === 'Banked').map((e) => e.who * 100000 + e.r));
    const out = { file: path.basename(f).replace(/\.json\.gz$/, ''), t: [{ runs: 0, rounds: 0, long: null }, { runs: 0, rounds: 0, long: null }] };
    for (const b of bodies) {
      const t = b.team;
      let r0 = null, x0 = 0, y0 = 0;
      const close = (r) => {
        if (r0 !== null && r - r0 >= 60) {
          const T = out.t[t]; T.runs++; T.rounds += r - r0;
          const c = S[r0][3].find((c) => c[0] === b.index);
          if (!T.long || r - r0 > T.long[1]) T.long = [b.type, r - r0, r0, x0, y0, c ? c[6] : 0];
        }
        r0 = null;
      };
      for (let r = 1; r <= final; r++) {
        const c = S[r][3].find((c) => c[0] === b.index);
        if (!c || !c[5] || cheb(c[1], c[2], spc[t][0], spc[t][1]) <= 2.6 || cap.has(b.index * 100000 + r)) { close(r); continue; }
        if (r0 === null) { r0 = r; x0 = c[1]; y0 = c[2]; continue; }
        if (cheb(c[1], c[2], x0, y0) > 1) { close(r); r0 = r; x0 = c[1]; y0 = c[2]; }
      }
      close(final + 1);
    }
    console.log(JSON.stringify(out));
  } catch (e) { console.log(JSON.stringify({ file: path.basename(f), err: String(e) })); }
}
