// Bag risk and recall reliability from bench replays (our team = A in NAME_A files, B in NAME_B files).
//   node tools/analysis/xm_econ.mjs BENCH_RUN_DIR
// Prints per team: gems banked, gems lost in bags at death, bag-size histogram at banking and at death,
// carrying hazard (deaths per body-round with a bag >= 1), recalls started / landed on spawn / interrupted.
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';
const dir = process.argv[2];
const files = fs.readdirSync(dir).filter((f) => f.endsWith('.repl26a')).sort();
const T = { us: {}, them: {} };
const add = (t, k, v = 1) => (T[t][k] = (T[t][k] || 0) + v);
for (const f of files) {
	const side = f.endsWith('_A.repl26a') ? 0 : 1;
	const d = await decode(unwrapReplay(fs.readFileSync(path.join(dir, f))), { every: 1 });
	const byR = new Map(d.rounds.map((r) => [r.r, r]));
	const spawn = [[], []];
	for (const c of d.rounds[0].ch) spawn[c[1]].push([c[3], c[4]]);
	const campTiles = new Set((d.meta.camps || []).map((c) => `${c.x},${c.y}`));
	const onSpawn = (team, x, y) => spawn[team].some(([a, b]) => Math.max(Math.abs(a - x), Math.abs(b - y)) <= 2);
	for (const e of d.events) {
		if (e.team === undefined) continue;
		const t = e.team === side ? 'us' : 'them';
		if (e.k === 'Banked') { add(t, 'banked', e.gems); add(t, 'banks'); add(t, `bank_${Math.min(6, Math.floor(e.gems / 10))}`); }
		if (e.k === 'Death') { add(t, 'deaths'); add(t, 'bagLost', e.bag); if (e.bag > 0) add(t, 'deathsWithBag'); add(t, `death_bag_${Math.min(6, Math.floor(e.bag / 10))}`); }
		if (e.k === 'Recall') {
			add(t, 'recalls');
			// Recall while capturing: standing on a camp tile when the recall starts; the reward must land first.
			const s0 = byR.get(e.r - 1), c0 = s0?.ch.find((q) => q[0] === e.who);
			if (c0 && campTiles.has(`${c0[3]},${c0[4]}`)) {
				add(t, 'capRecalls');
				const got = d.events.some((q) => q.k === 'CaptureGems' && q.who === e.who && q.r >= e.r - 6 && q.r <= e.r + 6);
				if (got) add(t, 'capRecallGot');
			}
			// Landed: on own spawn 5 rounds later and alive; otherwise interrupted (damage) or dead.
			const s = byR.get(e.r + 5), c = s?.ch.find((q) => q[0] === e.who);
			if (c && c[7] && onSpawn(c[1], c[3], c[4])) add(t, 'recallLanded');
			else if (c && !c[7]) add(t, 'recallDied');
			else add(t, 'recallInterrupted');
		}
	}
	// carrying exposure: body-rounds alive with gems > 0
	for (const r of d.rounds) for (const c of r.ch) if (c[7] && c[8] > 0) add(c[1] === side ? 'us' : 'them', 'carryRounds');
	for (const r of d.rounds) for (const c of r.ch) if (c[7]) add(c[1] === side ? 'us' : 'them', 'aliveRounds');
	for (const r of d.rounds) for (const c of r.ch) if (c[7]) add(c[1] === side ? 'us' : 'them', 'bagSum', c[8]);
}
for (const t of ['us', 'them']) {
	const x = T[t];
	console.log(`${t}: banked ${x.banked} in ${x.banks} banks (mean ${(x.banked / x.banks).toFixed(1)}), bag lost at death ${x.bagLost} (${(100 * x.bagLost / (x.banked + x.bagLost)).toFixed(1)}% of gathered), deaths ${x.deaths} (${x.deathsWithBag} with a bag)`);
	console.log(`   hazard: deaths per alive body-round ${(x.deaths / x.aliveRounds).toFixed(5)}, per carrying body-round ${(x.deathsWithBag / x.carryRounds).toFixed(5)}; mean bag carried ${(x.bagSum / x.aliveRounds).toFixed(1)}`);
	console.log(`   bank sizes (x10): ${[0, 1, 2, 3, 4, 5, 6].map((i) => x[`bank_${i}`] || 0).join(' ')} | bags at death (x10): ${[0, 1, 2, 3, 4, 5, 6].map((i) => x[`death_bag_${i}`] || 0).join(' ')}`);
	console.log(`   recalls ${x.recalls}: landed ${x.recallLanded || 0}, interrupted ${x.recallInterrupted || 0}, died ${x.recallDied || 0}; started on a camp tile ${x.capRecalls || 0}, reward captured ${x.capRecallGot || 0}`);
}
