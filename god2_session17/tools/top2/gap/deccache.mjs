#!/usr/bin/env node
// gap_g8: decode a replay once (tools/replay/decode.mjs, every round, items, camp hp, group rewards, wards) and cache the result
// gzipped, so the gap analyses (tools/top2/gap/*.mjs) load it in ~1 s instead of re-running the engine (~8 s a replay).
//   CAMBC_CACHE=... node tools/top2/gap/deccache.mjs OUTDIR replay   -> OUTDIR/<name>.json.gz, prints {"file": name, ok}
// Run over many replays with tools/live/par.py (3 workers max on the shared PC).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { decode } from '../../replay/decode.mjs';
const [outdir, file] = process.argv.slice(2);
const name = path.basename(file);
const dst = path.join(outdir, name.replace(/\.repl26a$/, '.json.gz'));
try {
  if (fs.existsSync(dst)) { console.log(JSON.stringify({ file: name, ok: 1, cached: 1 })); process.exit(0); }
  const d = await decode(fs.readFileSync(file));
  fs.writeFileSync(dst, zlib.gzipSync(JSON.stringify(d)));
  console.log(JSON.stringify({ file: name, ok: 1, rounds: d.meta.finalRound }));
} catch (e) {
  console.log(JSON.stringify({ file: name, ok: 0, err: String(e.message || e) }));
}
