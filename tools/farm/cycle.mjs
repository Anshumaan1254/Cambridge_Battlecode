// usage: node tools/farm/cycle.mjs FILE.repl26a TEAM(0|1) [TO] : per body, the capture / bank / recall / shop / death events in order (farming cycle)
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const [f, team, to] = process.argv.slice(2);
const d = await decode(fs.readFileSync(f));
const T = +team, R = +(to || 9999);
const by = {};
for (const e of d.events) {
  if (e.team !== T || e.r > R) continue;
  let s = null;
  if (e.k === 'CaptureGems') s = `cap${e.gems}@${e.at}`;
  else if (e.k === 'Banked') s = `bank${e.gems}@${e.at}`;
  else if (e.k === 'Recall') s = `recall@${e.from || ''}`;
  else if (e.k === 'Shop') s = 'shop';
  else if (e.k === 'Death') s = `DEATH@${e.at}`;
  else if (e.k === 'Teleport complete') s = 'tp';
  if (!s) continue;
  const k = `${e.champ}#${e.who}`;
  (by[k] = by[k] || []).push(`r${e.r}:${s}`);
}
for (const [k, v] of Object.entries(by)) {
  const out = []; for (const x of v) if (out[out.length - 1] !== x) out.push(x);
  console.log(k.padEnd(12), out.join(' '));
}
