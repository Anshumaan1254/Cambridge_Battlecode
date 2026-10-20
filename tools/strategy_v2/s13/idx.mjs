import fs from 'node:fs';
import path from 'node:path';
import { decode } from '../../replay/decode.mjs';
const dir = process.argv[2];
const rows = [];
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.repl26a')).sort()) {
  const d = await decode(fs.readFileSync(path.join(dir, f)));
  const [group, nn, side] = f.replace('.repl26a', '').split('_');
  const us = side === 'A' ? 0 : 1;
  const camps = {}; for (const c of d.meta.camps) camps[c.type] = (camps[c.type] ?? 0) + 1;
  const last = d.rounds[d.rounds.length - 1];
  rows.push({ group, nn, side, file: f, size: `${d.meta.width}x${d.meta.height}`, champs: d.meta.champsPerTeam, engine: d.meta.engine, rounds: d.rounds.length - 1,
    us_draft: d.meta.drafts[us], them_draft: d.meta.drafts[1 - us], outcome: d.meta.outcome, win: d.meta.outcome === us + 1, us_gems: last.sub[us], them_gems: last.sub[1 - us], camps });
}
fs.writeFileSync(path.join(dir, 'index.json'), JSON.stringify(rows, null, 1));
for (const r of rows) console.log(r.group, r.nn, r.side, r.size, r.champs, r.rounds, r.win ? 'WIN ' : 'loss', r.us_gems + '-' + r.them_gems, 'us', r.us_draft.join(','), '| them', r.them_draft.join(','), JSON.stringify(r.camps));
