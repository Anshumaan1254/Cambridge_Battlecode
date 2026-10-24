// Capture context for tools/teamplan/capture_check.py: every capture event (gems or gold-only) with the champions' state LAG rounds
// before it (when the capture began: capture_time = 5), one JSON object per line.
//   node tools/teamplan/capture_ctx.mjs [--lag 5] REPLAY_OR_DIR...
// Row: {replay, r, team, who, gems, gold, kind, at, before: [[index, team, type, x, y, hp, maxHp, alive, gems, gold, kills, items], ...]}
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../replay/decode.mjs';

const argv = process.argv.slice(2);
const li = argv.indexOf('--lag');
const lag = li >= 0 ? +argv[li + 1] : 5;
const files = [];
for (const a of argv.filter((x, i) => !x.startsWith('--') && !(li >= 0 && i === li + 1))) {
  if (fs.statSync(a).isDirectory()) for (const f of fs.readdirSync(a).sort()) { if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
  else files.push(a);
}
for (const f of files) {
  let d;
  try { d = await decode(fs.readFileSync(f), { goldCaptures: true, every: 1 }); }
  catch (err) { console.error(`${f}: ${err.message}`); continue; }
  const byRound = new Map(d.rounds.map((s) => [s.r, s.ch]));
  const name = path.basename(f, '.repl26a');
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' && e.k !== 'CaptureGold') continue;
    const before = byRound.get(e.r - lag);
    if (!before) continue;
    process.stdout.write(JSON.stringify({ replay: name, r: e.r, team: e.team, who: e.who, gems: e.gems, gold: e.gold,
      kind: e.k === 'CaptureGems' ? 'gems' : 'gold', at: e.at, before }) + '\n');
  }
}
