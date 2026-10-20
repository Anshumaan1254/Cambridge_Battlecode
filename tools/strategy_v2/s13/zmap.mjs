// zmap.mjs REPLAY: draw the zone plan (ZG lines) over the group tiles (G lines) of a LEGEND_TRACE replay, team a
import fs from 'node:fs';
import { unwrapReplay } from '../../replay/decode.mjs';
const f = process.argv[2];
const t = unwrapReplay(fs.readFileSync(f), 'team-a.stdout').toString('latin1');
let W = 0, H = 0, sp = null; const G = {}, Z = {}; const U = [];
for (let l of t.split('\n')) {
  l = l.replace(/\x00/g, '').trim();
  let m = l.match(/^M w=(\d+) h=(\d+) spawn=\((\d+),(\d+)\)/); if (m) { W = +m[1]; H = +m[2]; sp = [+m[3], +m[4]]; continue; }
  m = l.match(/^G id=(\d+) gems=(\d+) .* ours=(\d) d_ally=(\d+) hp=(\d+).* tiles=(.*)$/); if (m) { G[+m[1]] = { gems: +m[2], ours: +m[3], d: +m[4], hp: +m[5], tiles: m[6].split(';').filter(Boolean).map(s => s.split(',').map(Number)) }; continue; }
  m = l.match(/^ZG g=(\d+) z=(\d+)/); if (m) { Z[+m[1]] = +m[2]; continue; }
  m = l.match(/^ZU i=(\d+) type=(\d+) unit=(\d+)/); if (m) U.push(`${m[1]}:t${m[2]}u${m[3]}`);
}
const grid = Array.from({ length: H }, () => Array(W).fill('.'));
for (const [id, g] of Object.entries(G)) for (const [x, y] of g.tiles) grid[y][x] = id in Z ? String(Z[id]) : (g.ours ? '+' : '-');
grid[sp[1]][sp[0]] = 'S';
console.log(U.join(' '));
for (let y = 0; y < H; y++) console.log(grid[y].join(''));
