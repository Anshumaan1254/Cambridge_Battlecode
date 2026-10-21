// node tools/draftcheck.mjs REPLAY... : the two teams' drafts (pick order) of each replay (short games are enough: the draft is round 0).
// tools/draftcheck.sh BOT OPP MAPS plays 1-round games and calls this.
import fs from 'node:fs';
import { decode } from './replay/decode.mjs';
for (const f of process.argv.slice(2)) {
	let d;
	try { d = await decode(fs.readFileSync(f)); } catch (e) { console.log(f, 'decode failed', e.message); continue; }
	console.log(`${f.split('/').pop().replace('.repl26a', '').padEnd(34)} ${d.meta.champsPerTeam}  A ${d.meta.drafts[0].join(',').padEnd(44)} B ${d.meta.drafts[1].join(',')}`);
}
