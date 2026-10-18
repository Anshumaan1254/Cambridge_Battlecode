// Agent survive: for every death of a traced (XM_TRACE) team-A body, print its FC (combat estimate) lines and task lines
// for the rounds before the death.  node tools/analysis/pair_trace.mjs REPLAY [--back 6] [--champ Cassi,Issac]
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const opt = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const BACK = Number(opt('--back', 6));
const ONLY = args.includes('--champ') ? new Set(opt('--champ').split(',')) : null;
const f = args.find((a) => a.endsWith('.repl26a'));
const buf = fs.readFileSync(f);
const text = unwrapReplay(buf, 'team-a.stdout').toString('latin1').replace(/\0/g, '');
const lines = text.split('\n').filter((l) => l.startsWith('FC '));
const fc = new Map();
for (const l of lines) {
	const r = Number(/r=(\d+)/.exec(l)[1]), ty = Number(/ty=(\d+)/.exec(l)[1]);
	const k = `${r}:${ty}`;
	fc.set(k, l);
}
const d = await decode(unwrapReplay(buf), { every: 1 });
for (const e of d.events.filter((e) => e.k === 'Death' && e.team === 0)) {
	if (ONLY && !ONLY.has(e.champ)) continue;
	const ty = CHAMP.indexOf(e.champ);
	console.log(`death r${e.r} ${e.champ} bag ${e.bag}`);
	for (let r = e.r - BACK; r <= e.r; ++r) {
		const l = fc.get(`${r}:${ty}`);
		if (l) console.log('  ' + l.replace(/ (x|y|ohp|thp|odps|tdps|tt|inc|thp1|sc|mhp|gems)=[^ ]+/g, ''));
	}
}
console.log(`FC lines ${lines.length}`);
