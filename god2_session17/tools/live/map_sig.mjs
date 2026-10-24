#!/usr/bin/env node
// Map signatures for the in-bot A/B hash (bots/god/src/strat.cpp): width, height, total camps, per replay file -> JSON lines.
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
for (const file of process.argv.slice(2)) {
  try { const d = await decode(fs.readFileSync(file)); console.log(JSON.stringify({ file: file.split('/').pop(), W: d.meta.width, H: d.meta.height, camps: (d.meta.camps || []).length })); } catch (e) {}
}
