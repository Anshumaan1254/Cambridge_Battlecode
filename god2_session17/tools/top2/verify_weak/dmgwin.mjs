// verify_weak/dmgwin.mjs: damage/camp-damage/stun involving one body in a round window, plus nearest enemy distance per round
// Usage: node dmgwin.mjs DUMP BODY R0 R1
import fs from 'node:fs'; import zlib from 'node:zlib';
const [f, b, r0, r1] = process.argv.slice(2);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
const B = +b, A = +r0, Z = +r1;
const team = new Map(d.meta.bodies.map((x) => [x.index, x.team])), type = new Map(d.meta.bodies.map((x) => [x.index, x.type]));
const camps = new Map(d.meta.camps.map((c) => [c.index, c]));
const byR = new Map(d.R.map((x) => [x[0], x]));
for (let r = A; r <= Z; r++) {
  const row = byR.get(r); if (!row) continue;
  const me = row[3].find((c) => c[0] === B);
  const en = row[3].filter((c) => team.get(c[0]) !== team.get(B) && c[5]).map((c) => [type.get(c[0]), Math.max(Math.abs(c[1] - me[1]), Math.abs(c[2] - me[2])), c[1], c[2]]).sort((a, b) => a[1] - b[1]);
  const din = d.dmg.filter((x) => x[1] === r && x[3] === B).map((x) => (x[2] < 0 ? 'camp' + (-1 - x[2]) + ':' + camps.get(-1 - x[2])?.type : type.get(x[2])) + '=' + x[4]);
  const dout = d.dmg.filter((x) => x[1] === r && x[2] === B).map((x) => '>' + type.get(x[3]) + '=' + x[4] + (x[5] === 6 ? 's' + x[6] : ''));
  const cout = d.cdmg.filter((x) => x[1] === r && x[2] === B).map((x) => '>camp' + x[3] + ':' + camps.get(x[3])?.type + '@' + camps.get(x[3])?.x + ',' + camps.get(x[3])?.y + '=' + x[4]);
  const st = d.stun.filter((x) => x[1] === r && x[3] === B).map((x) => 'STUN by ' + (x[2] < 0 ? 'camp' : type.get(x[2])));
  console.log(r, `pos ${me[1]},${me[2]} hp ${me[3]} bag ${me[6]}`, 'enemies', JSON.stringify(en.slice(0, 3)), din.join(' '), dout.join(' '), cout.join(' '), st.join(' '));
}
