// Prediction audit for XM_TRACE builds of the legend bot (bots/_x_math): compares what the decision formulas
// predicted with what happened.
//
//   node tools/analysis/xm_audit.mjs BENCH_RUN_DIR [--fights] [--max N] [--json OUT]
//
// Reads every *.repl26a bundle in the directory (bench.py output: NAME_A = our bot is team A, NAME_B = team B),
// takes our team's stdout (team-a.stdout / team-b.stdout) and parses the trace lines:
//   GI  camp group facts (once per game)
//   FR  one farming round: predicted damage per round (ours, allies') and damage taken vs what happened
//   FE  one farming episode (commit -> group dead / switch / death): predicted kill time, damage, trips vs actual
//   FC  one fight estimate (combat()): advantage and its parts; --fights joins it with the replay to label the
//       outcome (deaths and health lost on both sides in the next H rounds)
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';

const argv = process.argv.slice(2);
const dir = argv[0];
const FIGHTS = argv.includes('--fights');
const maxI = argv.indexOf('--max');
const MAX = maxI >= 0 ? +argv[maxI + 1] : 1e9;
const jsonI = argv.indexOf('--json');
const H = 8; // fight outcome horizon (rounds)
const TYPES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];

function parse(line) {
	const sp = line.trim().split(/\s+/);
	const o = { k: sp[0] };
	for (const t of sp.slice(1)) {
		const i = t.indexOf('=');
		if (i < 0) continue;
		const key = t.slice(0, i), v = t.slice(i + 1);
		o[key] = /^-?[\d.]+$/.test(v) ? +v : v;
	}
	return o;
}

const files = fs.readdirSync(dir).filter((f) => f.endsWith('.repl26a')).sort().slice(0, MAX);
const FR = [], FE = [], FC = [], GI = [], DTH = [];
const fightRows = [];
for (const f of files) {
	const side = f.endsWith('_A.repl26a') ? 0 : 1;
	const buf = fs.readFileSync(path.join(dir, f));
	let text = '';
	try {
		text = unwrapReplay(buf, side === 0 ? 'team-a.stdout' : 'team-b.stdout').toString('latin1').replace(/\0/g, '');
	} catch (e) {
		continue;
	}
	const game = path.basename(f, '.repl26a');
	const lines = text.split('\n').filter((l) => /^(FR|FE|FC|FX|GI|DTH) /.test(l)).map(parse);
	// FX (printed just before its FC line) splits the fight estimate: own dps, allies, remembered enemies.
	const fx = new Map();
	for (const o of lines) if (o.k === 'FX') fx.set(`${o.r}:${o.ty}`, o);
	for (const o of lines) {
		o.game = game;
		if (o.k === 'FX') continue;
		if (o.k === 'FC') Object.assign(o, fx.get(`${o.r}:${o.ty}`) ? { ...fx.get(`${o.r}:${o.ty}`), k: 'FC' } : {});
		({ FR, FE, FC, GI, DTH })[o.k].push(o);
	}
	if (!FIGHTS) continue;
	// ---- fight outcomes from the replay
	const d = await decode(unwrapReplay(buf), { every: 1 });
	const byR = new Map(d.rounds.map((r) => [r.r, r]));
	// Camp attacks per round (to tile), with the camp's strength by type: wolf 20, elk 60, monolith 200 (GI lines).
	const CSTR = { wolf: 20, elk: 60, monolith: 200 };
	const campHits = new Map();
	for (const e of d.events)
		if (e.k === 'Attack' && e.camp !== undefined && e.to) {
			const t = d.meta.camps?.[e.camp]?.type;
			const key = `${e.r}:${e.to[0]},${e.to[1]}`;
			campHits.set(key, (campHits.get(key) || 0) + (CSTR[t] || 0));
		}
	// Spawn boxes: positions of each team in the first snapshot (+-2)
	const r0 = d.rounds[0];
	const spawn = [[], []];
	for (const c of r0.ch) spawn[c[1]].push([c[3], c[4]]);
	const onSpawn = (team, x, y) => spawn[team].some(([a, b]) => Math.max(Math.abs(a - x), Math.abs(b - y)) <= 2);
	// Fight episodes: per champion type, FC lines separated by <= 3 rounds belong together; keep the first.
	const fc = lines.filter((o) => o.k === 'FC').sort((a, b) => a.ty - b.ty || a.r - b.r);
	let last = {};
	for (const o of fc) {
		const prev = last[o.ty];
		last[o.ty] = o;
		const first = !prev || o.r - prev.r > 3;
		const anyFight = o.fight === 1;
		const s0 = byR.get(o.r - 1), s1 = byR.get(Math.min(o.r + H, d.rounds[d.rounds.length - 1].r));
		if (!s0 || !s1) continue;
		const me = s0.ch.find((c) => c[1] === side && c[2] === o.ty);
		if (!me) continue;
		const mx = o.x, my = o.y;
		const ours = s0.ch.filter((c) => c[1] === side && c[7] && Math.max(Math.abs(c[3] - mx), Math.abs(c[4] - my)) <= 6);
		const theirs = s0.ch.filter((c) => c[1] !== side && c[7] && Math.max(Math.abs(c[3] - mx), Math.abs(c[4] - my)) <= 9 && !onSpawn(c[1], c[3], c[4]));
		if (!theirs.length) continue;
		const ids = (arr) => new Set(arr.map((c) => c[0]));
		const oi = ids(ours), ti = ids(theirs);
		// Health lost and deaths over the horizon (a death counts the health it had left).
		const lost = { o: 0, t: 0 }, dead = { o: 0, t: 0 }, hp0 = { o: 0, t: 0 }, campDmg = { o: 0, t: 0 };
		for (const c of ours) hp0.o += c[5];
		for (const c of theirs) hp0.t += c[5];
		let meDead = false, tgtDead = false;
		const alive = new Map(s0.ch.map((c) => [c[0], c[7]]));
		const hpPrev = new Map(s0.ch.map((c) => [c[0], c[5]]));
		for (let r = o.r; r <= o.r + H; ++r) {
			const s = byR.get(r);
			if (!s) break;
			for (const c of s.ch) {
				const k = oi.has(c[0]) ? 'o' : ti.has(c[0]) ? 't' : null;
				if (!k || !alive.get(c[0])) continue;
				if (!c[7]) {
					lost[k] += hpPrev.get(c[0]);
					dead[k]++;
					alive.set(c[0], 0);
					if (c[0] === me[0]) meDead = true;
					if (k === 't' && c[2] === o.tt) tgtDead = true;
					// Cassi and Issac: one body's death kills the other; both count
				} else {
					const dl = hpPrev.get(c[0]) - c[5];
					// Spawn healing (+100%/round) and heals make health go up: only drops count.
					if (dl > 0) lost[k] += dl;
				}
				hpPrev.set(c[0], c[5]);
				const ch = campHits.get(`${r}:${c[3]},${c[4]}`);
				if (ch && c[7]) campDmg[k] += ch;
			}
		}
		fightRows.push({ game, r: o.r, ty: o.ty, first, fight: o.fight, adv: o.adv, tku: o.tku, tkt: o.tkt, ohp: o.ohp, thp: o.thp, odps: o.odps, tdps: o.tdps, na: o.na, ne: o.ne, kill: o.kill, reach: o.reach,
			esc: o.esc, iso: o.iso, sc: o.sc, fm: o.fm, mydps: o.mydps, ahp: o.ahp, adps: o.adps, mn: o.mn, mhp: o.mhp, mdps: o.mdps, rOurs: ours.length, rTheirs: theirs.length,
			allyD: ours.filter((c) => c[0] !== me[0]).map((c) => [Math.max(Math.abs(c[3] - mx), Math.abs(c[4] - my)), c[5]]),
			enemyD: theirs.map((c) => [Math.max(Math.abs(c[3] - mx), Math.abs(c[4] - my)), c[5]]),
			allyE: ours.filter((c) => c[0] !== me[0]).map((c) => [Math.min(...theirs.map((t) => Math.max(Math.abs(c[3] - t[3]), Math.abs(c[4] - t[4])))), c[5]]),
			meE: Math.min(...theirs.map((t) => Math.max(Math.abs(mx - t[3]), Math.abs(my - t[4])))), hp0o: hp0.o, hp0t: hp0.t, lostO: lost.o, lostT: lost.t, deadO: dead.o, deadT: dead.t, campO: campDmg.o, campT: campDmg.t, meDead, tgtDead, hp: o.hp, mhp: o.mhp, inc: o.inc, tdie: o.tdie });
		void anyFight;
	}
}

const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
const med = (a) => {
	if (!a.length) return NaN;
	const b = [...a].sort((x, y) => x - y);
	return b[Math.floor(b.length / 2)];
};
const fmt = (x, n = 2) => (Number.isFinite(x) ? x.toFixed(n) : 'nan');
const out = {};

// ---------------------------------------------------------------- FR: per-round damage dealt and taken
{
	console.log(`\n== FR farming rounds: ${FR.length} (games ${files.length})`);
	const rows = FR.filter((o) => !o.killed);
	console.log('Damage dealt per round, actual / predicted (sum over rounds; rounds where the group died are excluded: overkill)');
	console.log('type      | solo rounds  pred   actual  ratio | team rounds pred(my+ally) actual ratio | pred my-only ratio');
	for (let t = 0; t < 12; ++t) {
		const solo = rows.filter((o) => o.ty === t && o.claim === 0 && o.vis === 0 && o.clean);
		const team = rows.filter((o) => o.ty === t && (o.claim > 0 || o.vis > 0) && o.clean);
		if (!solo.length && !team.length) continue;
		const sp = sum(solo, (o) => o.myd), sa = sum(solo, (o) => o.dealt);
		const tp = sum(team, (o) => o.myd + o.ad), ta = sum(team, (o) => o.dealt), tm = sum(team, (o) => o.myd);
		console.log(`${TYPES[t].padEnd(9)} | ${String(solo.length).padStart(6)} ${fmt(sp / Math.max(1, solo.length), 1).padStart(7)} ${fmt(sa / Math.max(1, solo.length), 1).padStart(7)} ${fmt(sa / sp)} | ${String(team.length).padStart(6)} ${fmt(tp / Math.max(1, team.length), 1).padStart(7)} ${fmt(ta / Math.max(1, team.length), 1).padStart(7)} ${fmt(ta / tp)} | ${fmt(ta / tm)}`);
		out[`dealt_${TYPES[t]}`] = { solo: solo.length, soloRatio: sa / sp, team: team.length, teamRatio: ta / tp };
	}
	console.log('\nDamage taken per round (clean rounds: no enemy champion within 8), actual / predicted');
	console.log('type      | rounds  pred(in*share) actual ratio | nearest-camp model ratio | in(no share) ratio');
	for (let t = 0; t < 12; ++t) {
		const r = rows.filter((o) => o.ty === t && o.clean && o.share >= 0);
		if (!r.length) continue;
		const pp = sum(r, (o) => o.pin * o.share), aa = sum(r, (o) => o.lost);
		const mult = (o) => (o.j ? 0.7 : 1) * (o.du ? 0.9 : 1);
		const nn = sum(r, (o) => o.near * mult(o));
		const ii = sum(r, (o) => o.pin);
		console.log(`${TYPES[t].padEnd(9)} | ${String(r.length).padStart(6)} ${fmt(pp / r.length, 1).padStart(8)} ${fmt(aa / r.length, 1).padStart(7)} ${fmt(aa / pp)} | ${fmt(aa / nn)} | ${fmt(aa / ii)}`);
		out[`taken_${TYPES[t]}`] = { n: r.length, ratioShare: aa / pp, ratioNear: aa / nn, ratioIn: aa / ii };
	}
	// Absolute error of the two incoming models, per round (clean rounds)
	const r = rows.filter((o) => o.clean && o.share >= 0);
	const mult = (o) => (o.j ? 0.7 : 1) * (o.du ? 0.9 : 1);
	const mae = (f) => sum(r, (o) => Math.abs(f(o) - o.lost)) / Math.max(1, r.length);
	const bias = (f) => sum(r, (o) => f(o) - o.lost) / Math.max(1, r.length);
	console.log(`incoming models over ${r.length} clean rounds: in*share MAE ${fmt(mae((o) => o.pin * o.share), 1)} bias ${fmt(bias((o) => o.pin * o.share), 1)} | nearest-camp MAE ${fmt(mae((o) => o.near * mult(o)), 1)} bias ${fmt(bias((o) => o.near * mult(o)), 1)} | mean actual ${fmt(sum(r, (o) => o.lost) / r.length, 1)}`);
	out.incoming = { n: r.length, maeShare: mae((o) => o.pin * o.share), biasShare: bias((o) => o.pin * o.share), maeNear: mae((o) => o.near * mult(o)), biasNear: bias((o) => o.near * mult(o)) };
}

// ---------------------------------------------------------------- FE: farming episodes
{
	console.log(`\n== FE farming episodes: ${FE.length}`);
	const why = {};
	for (const o of FE) why[o.why] = (why[o.why] || 0) + 1;
	console.log('episode ends:', JSON.stringify(why));
	const eng = FE.filter((o) => o.eng >= 0);
	const why2 = {};
	for (const o of eng) why2[o.why] = (why2[o.why] || 0) + 1;
	console.log('engaged episodes ends:', JSON.stringify(why2));
	const short = FE.filter((o) => o.why === 'switch' && o.eng < 0 && o.atot <= 2).length;
	console.log(`target flips (switch within 2 rounds, never engaged): ${short} = ${fmt(short / FE.length * 100, 1)}% of episodes`);
	const ab = eng.filter((o) => o.why === 'switch');
	console.log(`abandoned after engaging: ${ab.length}, mean rounds engaged ${fmt(sum(ab, (o) => o.ak) / Math.max(1, ab.length), 1)}, group hp left at engage ${fmt(sum(ab, (o) => o.hp0) / Math.max(1, ab.length), 0)}`);
	const kills = eng.filter((o) => o.why === 'kill' && o.plan === 1);
	const cls = (o) => (o.mono ? 'monolith' : o.elk ? 'elk' : o.gems === 0 ? 'gold' : o.n >= 3 && o.pin > 0 ? 'pack' : o.pin > 0 ? 'small' : 'gem/harmless');
	const groups = {};
	for (const o of kills) (groups[cls(o)] ??= []).push(o);
	console.log('Kill time (engage -> group dead) and damage taken, actual vs predicted at commit (pred kill = hp/(my+ally dps) + trips x trip_cost)');
	console.log('class        n   pred kill  act kill  ratio(med) | pred taken  act lost  ratio | pred trips act trips | pred time act time(commit->dead)');
	for (const [k, a] of Object.entries(groups)) {
		// Predictions were made at commit for the HP then; scale to the HP at engage (allies may have hit it meanwhile).
		const pk = a.map((o) => o.pk * (o.ghpc > 0 ? o.hp0 / o.ghpc : 1));
		const ak = a.map((o) => o.ak);
		const rk = a.map((o, i) => ak[i] / Math.max(1, pk[i]));
		const pt = sum(a, (o) => o.ptk), lt = sum(a, (o) => o.lost);
		const ptime = a.map((o) => o.peta + o.pwait + o.pk + o.ptr * o.tc);
		console.log(`${k.padEnd(12)} ${String(a.length).padStart(4)} ${fmt(sum(pk, (x) => x) / a.length, 1).padStart(9)} ${fmt(sum(ak, (x) => x) / a.length, 1).padStart(9)} ${fmt(med(rk)).padStart(8)} | ${fmt(pt / a.length, 0).padStart(9)} ${fmt(lt / a.length, 0).padStart(9)} ${fmt(lt / Math.max(1, pt))} | ${fmt(sum(a, (o) => o.ptr) / a.length).padStart(6)} ${fmt(sum(a, (o) => o.trips) / a.length).padStart(6)} | ${fmt(sum(ptime, (x) => x) / a.length, 1).padStart(7)} ${fmt(sum(a, (o) => o.atot) / a.length, 1).padStart(7)}`);
		out[`kill_${k}`] = { n: a.length, predKill: sum(pk, (x) => x) / a.length, actKill: sum(ak, (x) => x) / a.length, medRatio: med(rk), predTaken: pt / a.length, actLost: lt / a.length, predTrips: sum(a, (o) => o.ptr) / a.length, actTrips: sum(a, (o) => o.trips) / a.length };
	}
	// Travel: predicted eta at commit vs rounds to engage
	const tr = kills.filter((o) => o.pwait === 0);
	console.log(`travel (no wait): pred eta ${fmt(sum(tr, (o) => o.peta) / Math.max(1, tr.length), 1)} actual commit->engage ${fmt(sum(tr, (o) => o.eng - o.commit) / Math.max(1, tr.length), 1)} over ${tr.length}`);
}

// ---------------------------------------------------------------- FC: fights
if (FIGHTS) {
	console.log(`\n== FC fight estimates: ${FC.length} lines, ${fightRows.length} with enemies in the replay window`);
	const firsts = fightRows.filter((o) => o.first);
	const label = (o) => (o.deadT > o.deadO ? 1 : o.deadT < o.deadO ? 0 : o.lostT / Math.max(1, o.hp0t) > o.lostO / Math.max(1, o.hp0o) ? 0.5 + 0.0001 : 0.5 - 0.0001);
	const win = (o) => (o.deadT > o.deadO || (o.deadT === o.deadO && o.lostT / Math.max(1, o.hp0t) > o.lostO / Math.max(1, o.hp0o)) ? 1 : 0);
	for (const [name, set] of [['all episode starts', firsts], ['episode starts where we chose to fight', firsts.filter((o) => o.fight)], ['all fight=1 turns', fightRows.filter((o) => o.fight)]]) {
		console.log(`\n-- ${name}: ${set.length}`);
		console.log('adv bin       n   win%  ourDeaths theirDeaths  realised adv (geo mean)  meDead%');
		const bins = [0, 0.25, 0.5, 0.75, 1, 1.3, 1.6, 2, 3, 5, 1e9];
		for (let b = 0; b + 1 < bins.length; ++b) {
			const a = set.filter((o) => o.adv >= bins[b] && o.adv < bins[b + 1]);
			if (!a.length) continue;
			const real = a.filter((o) => o.lostO > 0 && o.lostT > 0).map((o) => Math.log((o.lostT / o.hp0t) / (o.lostO / o.hp0o)));
			console.log(`${fmt(bins[b])}-${bins[b + 1] > 1e8 ? 'inf ' : fmt(bins[b + 1])} ${String(a.length).padStart(5)} ${fmt(100 * sum(a, win) / a.length, 0).padStart(5)} ${fmt(sum(a, (o) => o.deadO) / a.length).padStart(9)} ${fmt(sum(a, (o) => o.deadT) / a.length).padStart(10)} ${fmt(real.length ? Math.exp(sum(real, (x) => x) / real.length) : NaN).padStart(16)} (${real.length}) ${fmt(100 * sum(a, (o) => (o.meDead ? 1 : 0)) / a.length, 0).padStart(6)}`);
		}
		// Logistic fit P(win) = 1/(1+exp(-(a + b log adv))) by Newton's method
		const xs = set.filter((o) => o.adv > 0).map((o) => [Math.log(o.adv), win(o)]);
		let A = 0, B = 1;
		for (let it = 0; it < 50; ++it) {
			let g0 = 0, g1 = 0, h00 = 0, h01 = 0, h11 = 0;
			for (const [x, y] of xs) {
				const p = 1 / (1 + Math.exp(-(A + B * x)));
				g0 += y - p, g1 += (y - p) * x;
				const w = p * (1 - p);
				h00 += w, h01 += w * x, h11 += w * x * x;
			}
			const det = h00 * h11 - h01 * h01;
			if (Math.abs(det) < 1e-9) break;
			A += (h11 * g0 - h01 * g1) / det;
			B += (-h01 * g0 + h00 * g1) / det;
		}
		const ll = (a, b) => sum(xs, ([x, y]) => { const p = 1 / (1 + Math.exp(-(a + b * x))); return y ? Math.log(Math.max(1e-9, p)) : Math.log(Math.max(1e-9, 1 - p)); });
		const brier = sum(xs, ([x, y]) => { const p = 1 / (1 + Math.exp(-(A + B * x))); return (p - y) ** 2; }) / Math.max(1, xs.length);
		const acc1 = sum(xs, ([x, y]) => ((x > 0) === (y === 1) ? 1 : 0)) / Math.max(1, xs.length);
		console.log(`logistic P(win) = s(${fmt(A, 3)} + ${fmt(B, 3)} ln adv): 50% at adv = ${fmt(Math.exp(-A / B), 3)}; accuracy of "adv>1 wins" ${fmt(100 * acc1, 1)}%; brier ${fmt(brier, 3)}; n ${xs.length}`);
		// Regression of realised log advantage on predicted log advantage
		const rr = set.filter((o) => o.lostO > 0 && o.lostT > 0 && o.adv > 0).map((o) => [Math.log(o.adv), Math.log((o.lostT / o.hp0t) / (o.lostO / o.hp0o))]);
		if (rr.length > 5) {
			const mx = sum(rr, (p) => p[0]) / rr.length, my = sum(rr, (p) => p[1]) / rr.length;
			const sxy = sum(rr, (p) => (p[0] - mx) * (p[1] - my)), sxx = sum(rr, (p) => (p[0] - mx) ** 2), syy = sum(rr, (p) => (p[1] - my) ** 2);
			console.log(`realised ln adv = ${fmt(my - (sxy / sxx) * mx, 3)} + ${fmt(sxy / sxx, 3)} x predicted ln adv (r = ${fmt(sxy / Math.sqrt(sxx * syy), 3)}, n ${rr.length}); mean predicted ln adv ${fmt(mx, 3)}, mean realised ${fmt(my, 3)} -> bias x${fmt(Math.exp(mx - my), 2)}`);
		}
		out[`fight_${name}`] = { n: set.length, A, B, adv50: Math.exp(-A / B), acc1, brier };
		void label;
	}
	// Components: predicted DPS vs realised (episode starts where we fought, both sides took damage)
	const comp = firsts.filter((o) => o.fight && o.lostO > 0 && o.lostT > 0);
	const ourDpsReal = sum(comp, (o) => o.lostT / H), ourDpsPred = sum(comp, (o) => o.odps);
	const thDpsReal = sum(comp, (o) => o.lostO / H), thDpsPred = sum(comp, (o) => o.tdps);
	console.log(`\nfought episodes (${comp.length}): our dps pred ${fmt(ourDpsPred / comp.length, 1)} realised (their hp lost / ${H}) ${fmt(ourDpsReal / comp.length, 1)}; their dps pred ${fmt(thDpsPred / comp.length, 1)} realised ${fmt(thDpsReal / comp.length, 1)}`);
	console.log(`participants: model allies+1 ${fmt(sum(comp, (o) => o.na + 1) / comp.length)} replay ours ${fmt(sum(comp, (o) => o.rOurs) / comp.length)}; model enemies ${fmt(sum(comp, (o) => o.ne) / comp.length)} replay theirs ${fmt(sum(comp, (o) => o.rTheirs) / comp.length)}`);
	console.log(`hp: model ours ${fmt(sum(comp, (o) => o.ohp) / comp.length, 0)} replay ${fmt(sum(comp, (o) => o.hp0o) / comp.length, 0)}; model theirs ${fmt(sum(comp, (o) => o.thp) / comp.length, 0)} replay ${fmt(sum(comp, (o) => o.hp0t) / comp.length, 0)}`);
	// Escape feasibility: episodes where we did not fight and were in reach
	const fled = firsts.filter((o) => !o.fight && o.reach);
	const esc1 = fled.filter((o) => o.esc), esc0 = fled.filter((o) => !o.esc);
	console.log(`in reach and did not fight: ${fled.length}; predicted escapable ${esc1.length} died ${fmt(100 * sum(esc1, (o) => (o.meDead ? 1 : 0)) / Math.max(1, esc1.length), 1)}% | predicted cornered ${esc0.length} died ${fmt(100 * sum(esc0, (o) => (o.meDead ? 1 : 0)) / Math.max(1, esc0.length), 1)}%`);
	const fo = firsts.filter((o) => o.fight);
	console.log(`chose to fight: ${fo.length}, died ${fmt(100 * sum(fo, (o) => (o.meDead ? 1 : 0)) / Math.max(1, fo.length), 1)}%, killed target ${fmt(100 * sum(fo, (o) => (o.tgtDead ? 1 : 0)) / Math.max(1, fo.length), 1)}%`);
	const kl = firsts.filter((o) => o.kill);
	console.log(`"killable" episodes: ${kl.length}, target died within ${H}: ${fmt(100 * sum(kl, (o) => (o.tgtDead ? 1 : 0)) / Math.max(1, kl.length), 1)}%`);
	out.fightRows = fightRows.length;
}
if (jsonI >= 0) fs.writeFileSync(argv[jsonI + 1], JSON.stringify({ out, FR: FR.length, FE: FE.length, fightRows }, null, 0));
