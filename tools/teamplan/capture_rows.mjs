// Capture rows (gem and gold-only captures) from replays, one JSON object per line on stdout.
//   node tools/teamplan/capture_rows.mjs REPLAY_OR_DIR...
// Each row: {replay, r, team, who, champ, gems, gold, kind, at}; kind 'gems' (CaptureGems) or 'gold' (CaptureGold, gold-only groups); at =
// the capturer's tile.
// Uses tools/replay/decode.mjs with opts.goldCaptures (gold-only captures are not in the default event list).
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../replay/decode.mjs';

const files = [];
for (const a of process.argv.slice(2)) {
  if (fs.statSync(a).isDirectory()) for (const f of fs.readdirSync(a).sort()) { if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
  else files.push(a);
}
if (!files.length) { console.error('usage: capture_rows.mjs REPLAY_OR_DIR...'); process.exit(2); }
for (const f of files) {
  let d;
  try { d = await decode(fs.readFileSync(f), { goldCaptures: true }); }
  catch (err) { console.error(`${f}: ${err.message}`); continue; }
  const name = path.basename(f, '.repl26a');
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' && e.k !== 'CaptureGold') continue;
    process.stdout.write(JSON.stringify({ replay: name, r: e.r, team: e.team, who: e.who, champ: e.champ, gems: e.gems, gold: e.gold,
      kind: e.k === 'CaptureGems' ? 'gems' : 'gold', at: e.at }) + '\n');
  }
}
