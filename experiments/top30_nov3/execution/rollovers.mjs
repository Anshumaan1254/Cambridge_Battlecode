#!/usr/bin/env node
// Turn rollovers (a turn that ran out of fuel and continues next round; step kind 26) and bot errors (27) per replay.
//   node execution/rollovers.mjs <out.jsonl> replay1.repl26a replay2 ...   (appends one line per replay: {key, final, roll: [[r, who]...], err: [[r, who]...]})
import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../../../tools/replay/decode.mjs';
process.removeAllListeners('warning');
const [outf, ...files] = process.argv.slice(2);
for (const f of files) {
  const key = path.basename(f, '.repl26a');
  try {
    const res = await decode(fs.readFileSync(f), { every: 100000, rollovers: true });
    const roll = res.events.filter((e) => e.k === 'Turn rollover').map((e) => [e.r, e.who ?? null, e.team ?? null]);
    const err = res.events.filter((e) => e.k === 'Bot error').map((e) => [e.r, e.who ?? null, e.team ?? null]);
    fs.appendFileSync(outf, JSON.stringify({ key, final: res.meta.finalRound, roll, err }) + '\n');
  } catch (e) {
    fs.appendFileSync(outf, JSON.stringify({ key, error: String(e).slice(0, 200) }) + '\n');
  }
}
