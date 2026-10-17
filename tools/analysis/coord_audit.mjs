#!/usr/bin/env node
// Team-coordination audit from bench replays (tools/bench.py output directories).
//
//   node tools/analysis/coord_audit.mjs [--json out.json] [--split] DIR_OR_FILE...
//
// "us" = bench BOT_A (NAME_A.repl26a: team A, NAME_B.repl26a: team B); "them" = the opponent in the same games.
// Every number is reported for both sides so a failure can be compared with what the opponent suffers.
// --split also prints the "us" side for games we won and games we lost separately.
//
// Definitions (positions are the end-of-round snapshot of the round before the event unless noted):
//   death         a body's alive flag going false. "primary" = the body actually killed; for Cassi & Issac the
//                 partner that dies with it is a "linked" death (not counted in the per-death categories).
//   champ death   primary death whose killer is an enemy champion (the step that killed was its attack or cast).
//   alone6        champ death with no other living body of our team (linked partner excluded) within 6 tiles.
//   near_nojoin   champ death with an ally within 10 tiles, but no ally within 10 hit an enemy champion in the
//                 3 rounds before (r-3..r): help was close and did not come.
//   outnum_local  champ death where enemy bodies within 6 outnumber our bodies within 6 (victim included) while
//                 the whole team was not outnumbered (our alive >= their alive): the team was elsewhere.
//   abandoned     champ death where an ally that was within 6 at r-4 and in the fight (hit or was hit by an
//                 enemy champion in r-6..r-3) is farther at r-1 and did not hit anyone in r-2..r: it walked away.
//   hit           an attack, or a damage/stun cast, whose target tile is an enemy champion's live position
//                 (radius 1 for area spells). Dash, reset, shield and heal casts are not hits.
//   kill assists  for each enemy champ death by us: our distinct bodies that hit the victim in r-5..r.
//   focus         rounds in which 2+ of our bodies hit enemy champions within 8 tiles of each other: "focused"
//                 when every single-target hit of those bodies that round went to the same enemy.
//   episode       champion-vs-champion hits grouped into fights (a hit joins an open fight within 8 tiles whose
//                 last hit was <= 3 rounds ago). Participants = bodies that hit or were hit. idle_near = our
//                 living bodies within 10 of the fight (at its start) that never took part.
//   walk-out      the first round a respawned body is off its spawn region; "alone" = no living ally within 4.
//                 died40 = it died within 40 rounds of walking out.
//   lone_rounds   alive body-rounds with no other living body of our team within 8 (spread).
//   cost          gem-equivalent loss of a death: bag + 25 (60 rounds of one body's farming) + 11 (50 gold
//                 kill bounty to them x 0.22).
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { decode, unwrapReplay, findEngineWasms } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const KIT = {
	Ryth: ['aoe_stun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'cc0'],
	Issac: ['reset', 'dash'], Stellar: ['dmg', 'aoe'], Prism: ['cc', 'aoe'], Marcella: ['reset', 'dmg'], Willow: ['heal', 'reset'],
	Ren: ['cc', 'dash'], Varg: ['reset', 'shield'], Tavi: ['reset', 'cc'],
};
const SELF_CAST = new Set(['dash', 'reset', 'shield', 'heal']);
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const DEATH_COST = 25 + 11;

let engine = null;
async function spawnRegions(buf) {
	if (!engine) {
		const wasi = new WASI({ version: 'preview1', args: [], env: {} });
		const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
		const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
		wasi.initialize(inst);
		engine = { X: inst.exports, out: inst.exports.Engine_Malloc(64) };
	}
	const { X, out } = engine;
	const dv = () => new DataView(X.memory.buffer);
	const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
	const p = X.Engine_Malloc(buf.length);
	new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
	chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load');
	const g = dv().getBigUint64(out, true);
	X.Engine_Free(p);
	chk(X.Game_GetBitboardMetadata(g, out), 'meta');
	const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
	chk(X.Game_GetSymmetry(g, out), 'sym');
	const sym = dv().getInt32(out, true);
	chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
	const sp = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
	const mirror = (x, y) => (sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y]);
	const A = new Set(), B = new Set();
	for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) {
		A.add(x + ',' + y);
		const [mx, my] = mirror(x, y);
		B.add(mx + ',' + my);
	}
	return [A, B];
}

const ZERO = () => ({
	games: 0, wins: 0, deaths: 0, linked: 0, champDeaths: 0, campDeaths: 0, bagLost: 0, bagLostChamp: 0, cost: 0,
	alone6: 0, alone6Bag: 0, alone6Cost: 0, nearNoJoin: 0, nearNoJoinCost: 0, outnumLocal: 0, outnumLocalCost: 0,
	abandoned: 0, abandonedCost: 0, joinedDeaths: 0, carrier20: 0,
	kills: 0, killHitters: 0, soloKills: 0, multiRounds: 0, focusedRounds: 0, hits: 0,
	episodes: 0, epWon: 0, epLost: 0, epEven: 0, epIdleNear: 0, epIdleNearLost: 0, epOutnum: 0, epOutnumLost: 0, epOutnumGlobalOk: 0,
	epDiff: 0, epDiffOutnum: 0, epDiffEven: 0, epDiffMore: 0, epN_outnum: 0, epN_even: 0, epN_more: 0, epSolo: 0, epSoloLost: 0,
	walkouts: 0, walkoutsAlone: 0, aloneDied: 0, groupDied: 0, walkoutsDeficit: 0, walkoutsDeficitAlone: 0,
	aliveRounds: 0, loneRounds: 0, fightBodyRounds: 0, fightOutnum: 0,
});

function add(acc, g) { for (const k of Object.keys(g)) acc[k] = (acc[k] || 0) + g[k]; }

async function analyse(file) {
	const raw = fs.readFileSync(file);
	const buf = unwrapReplay(raw);
	const ourTeam = /_B\.repl26a$/.test(file) ? 1 : 0;
	const d = await decode(buf, { every: 1 });
	const spawns = await spawnRegions(buf);
	const R = new Map(d.rounds.map((x) => [x.r, x]));
	const snap = (r) => R.get(r) || R.get(r - 1) || R.get(r + 1);
	const type = {}, team = {};
	for (const b of d.meta.bodies) { type[b.index] = b.type; team[b.index] = b.team; }
	const partner = (w) => {
		if (type[w] !== 'Cassi' && type[w] !== 'Issac') return -1;
		const want = type[w] === 'Cassi' ? 'Issac' : 'Cassi';
		const p = d.meta.bodies.find((b) => b.team === team[w] && b.type === want);
		return p ? p.index : -1;
	};
	const S = [ZERO(), ZERO()]; // per team
	const winner = d.meta.outcome === 1 ? 0 : d.meta.outcome === 2 ? 1 : -1;
	for (let t = 0; t < 2; t++) { S[t].games = 1; S[t].wins = winner === t ? 1 : 0; }
	const pos = (r, w) => { const s = snap(r); const c = s && s.ch.find((q) => q[0] === w); return c && c[7] ? [c[3], c[4]] : null; };
	const aliveAt = (r, t) => { const s = snap(r); return s ? s.ch.filter((c) => c[1] === t && c[7]) : []; };

	// Pass 1: hits (with live positions), deaths with their killing step.
	const hits = []; // {r, a, v, at}
	const deaths = []; // {r, who, at, bag, by, primary}
	let curR = -1, live = {};
	const startState = (r) => {
		const prev = snap(r - 1);
		live = {};
		if (prev) for (const c of prev.ch) live[c[0]] = { pos: [c[3], c[4]], alive: !!c[7] };
	};
	let lastTo = null, lastRad = 0;
	for (const e of d.events) {
		if (e.r !== curR) { curR = e.r; startState(curR); }
		if (e.k === 'Death') {
			const primary = lastTo ? cheb(e.at, lastTo) <= lastRad : true;
			deaths.push({ r: e.r, who: e.who, at: e.at, bag: e.bag || 0, by: e.by, primary });
			if (live[e.who]) live[e.who].alive = false;
			continue;
		}
		if (e.k === 'Attack' || e.k === 'Cast ability') {
			lastTo = e.to || null;
			lastRad = e.k === 'Cast ability' && e.who !== undefined && KIT[type[e.who]]?.[e.slot]?.startsWith('aoe') ? 1 : 0;
		}
		if (e.who === undefined) continue;
		const w = e.who;
		if (e.k === 'Move' && live[w]) { live[w].pos = e.to; continue; }
		if (e.k === 'Cast ability') {
			const kind = KIT[type[w]]?.[e.slot];
			if (kind === 'dash' && e.to && live[w]) live[w].pos = e.to;
			if (!kind || SELF_CAST.has(kind) || !e.to) continue;
			const rad = kind.startsWith('aoe') ? 1 : 0;
			for (const [v, c] of Object.entries(live))
				if (team[v] !== team[w] && c.alive && cheb(c.pos, e.to) <= rad)
					hits.push({ r: e.r, a: w, v: +v, at: c.pos.slice(), apos: live[w]?.pos?.slice(), single: rad === 0 });
			continue;
		}
		if (e.k === 'Attack' && e.to) {
			for (const [v, c] of Object.entries(live))
				if (team[v] !== team[w] && c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1])
					hits.push({ r: e.r, a: w, v: +v, at: c.pos.slice(), apos: live[w]?.pos?.slice(), single: true });
		}
	}
	// C&I: when both die in the same round, the one at the killing tile is primary, the other linked.
	for (const x of deaths) {
		const p = partner(x.who);
		if (p < 0) continue;
		const y = deaths.find((z) => z.who === p && z.r === x.r);
		if (!y) continue;
		if (x.primary && y.primary) { // both at the killing tile (adjacent) or unknown: keep the first as primary
			if (deaths.indexOf(y) < deaths.indexOf(x)) x.primary = false; else y.primary = false;
		}
	}
	const hitsBy = (w, r0, r1) => hits.some((h) => h.a === w && h.r >= r0 && h.r <= r1);
	const hitOrHit = (w, r0, r1) => hits.some((h) => (h.a === w || h.v === w) && h.r >= r0 && h.r <= r1);

	// Deaths.
	for (const x of deaths) {
		const t = team[x.who], s = S[t];
		s.deaths++;
		s.bagLost += x.bag;
		if (!x.primary) { s.linked++; continue; }
		const cost = x.bag + DEATH_COST;
		s.cost += cost;
		if (typeof x.by !== 'number' || team[x.by] === t) { s.campDeaths++; continue; }
		s.champDeaths++;
		s.bagLostChamp += x.bag;
		if (x.bag >= 20) s.carrier20++;
		const p = partner(x.who);
		const mates = aliveAt(x.r - 1, t).filter((c) => c[0] !== x.who && c[0] !== p);
		const foes = aliveAt(x.r - 1, 1 - t);
		const dist = (c) => cheb([c[3], c[4]], x.at);
		const near6 = mates.filter((c) => dist(c) <= 6), near10 = mates.filter((c) => dist(c) <= 10);
		const joined = near10.some((c) => hitsBy(c[0], x.r - 3, x.r));
		if (joined) s.joinedDeaths++;
		if (!near6.length) { s.alone6++; s.alone6Bag += x.bag; s.alone6Cost += cost; }
		if (near10.length && !joined) { s.nearNoJoin++; s.nearNoJoinCost += cost; }
		// Local numbers: bodies within 6 of the death (victim and partner count as ours).
		const oursLocal = 1 + near6.length + (p >= 0 && pos(x.r - 1, p) && cheb(pos(x.r - 1, p), x.at) <= 6 ? 1 : 0);
		const theirsLocal = foes.filter((c) => dist(c) <= 6).length;
		const ourAlive = aliveAt(x.r - 1, t).length, theirAlive = foes.length;
		if (theirsLocal > oursLocal && ourAlive >= theirAlive) { s.outnumLocal++; s.outnumLocalCost += cost; }
		// Abandoned: a fighting ally within 6 four rounds ago walked away and stopped hitting.
		const was = aliveAt(x.r - 4, t).filter((c) => c[0] !== x.who && c[0] !== p);
		const vpos4 = pos(x.r - 4, x.who);
		if (vpos4) for (const c of was) {
			const d4 = cheb([c[3], c[4]], vpos4);
			if (d4 > 6 || !hitOrHit(c[0], x.r - 6, x.r - 3)) continue;
			const now = pos(x.r - 1, c[0]);
			if (!now) continue;
			if (cheb(now, x.at) > d4 && !hitsBy(c[0], x.r - 2, x.r)) { s.abandoned++; s.abandonedCost += cost; break; }
		}
	}
	// Kills and assists (enemy primary deaths by our champions).
	for (const x of deaths) {
		if (!x.primary || typeof x.by !== 'number') continue;
		const kt = team[x.by];
		if (kt === team[x.who]) continue;
		const s = S[kt];
		s.kills++;
		const hitters = new Set(hits.filter((h) => h.v === x.who && h.r >= x.r - 5 && h.r <= x.r && team[h.a] === kt).map((h) => h.a));
		hitters.add(x.by);
		s.killHitters += hitters.size;
		if (hitters.size === 1) s.soloKills++;
	}
	// Focus fire per round.
	const byRound = new Map();
	for (const h of hits) { const k = h.r * 2 + team[h.a]; if (!byRound.has(k)) byRound.set(k, []); byRound.get(k).push(h); }
	for (const [k, hs] of byRound) {
		const t = k % 2, s = S[t];
		s.hits += hs.length;
		const single = hs.filter((h) => h.single);
		const attackers = [...new Set(single.map((h) => h.a))];
		if (attackers.length < 2) continue;
		// same fight: attackers within 8 of each other (use first attacker's position)
		const ap = attackers.map((a) => single.find((h) => h.a === a).apos).filter(Boolean);
		if (ap.length < 2 || !ap.every((p) => cheb(p, ap[0]) <= 8)) continue;
		s.multiRounds++;
		if (new Set(single.map((h) => h.v)).size === 1) s.focusedRounds++;
	}
	// Episodes.
	const eps = [];
	for (const h of [...hits].sort((a, b) => a.r - b.r)) {
		let ep = eps.find((e) => h.r - e.last <= 3 && cheb(e.center, h.at) <= 8);
		if (!ep) { ep = { start: h.r, last: h.r, center: h.at, part: new Set(), deaths: [0, 0] }; eps.push(ep); }
		ep.last = h.r;
		ep.center = h.at;
		ep.part.add(h.a); ep.part.add(h.v);
	}
	for (const x of deaths) {
		if (typeof x.by !== 'number' || team[x.by] === team[x.who]) continue;
		const killer = x.primary ? x.who : partner(x.who);
		const ep = eps.find((e) => x.r >= e.start && x.r <= e.last + 1 && e.part.has(killer) && e.part.has(x.by));
		if (ep) ep.deaths[team[x.who]]++;
	}
	for (const ep of eps) {
		for (let t = 0; t < 2; t++) {
			const s = S[t];
			const mine = [...ep.part].filter((w) => team[w] === t);
			const theirs = [...ep.part].filter((w) => team[w] !== t);
			s.episodes++;
			const diff = ep.deaths[1 - t] - ep.deaths[t];
			s.epDiff += diff;
			if (diff > 0) s.epWon++; else if (diff < 0) s.epLost++; else s.epEven++;
			const idle = aliveAt(ep.start - 1, t).filter((c) => !ep.part.has(c[0]) && cheb([c[3], c[4]], ep.center) <= 10);
			if (idle.length) { s.epIdleNear++; if (diff < 0) s.epIdleNearLost++; }
			if (mine.length === 1) { s.epSolo++; if (diff < 0) s.epSoloLost++; }
			if (mine.length < theirs.length) {
				s.epOutnum++; s.epN_outnum++; s.epDiffOutnum += diff;
				if (diff < 0) s.epOutnumLost++;
				if (aliveAt(ep.start - 1, t).length >= aliveAt(ep.start - 1, 1 - t).length) s.epOutnumGlobalOk++;
			} else if (mine.length === theirs.length) { s.epN_even++; s.epDiffEven += diff; }
			else { s.epN_more++; s.epDiffMore += diff; }
		}
	}
	// Spread and fight rounds (snapshot per round).
	const fightRounds = new Set(hits.flatMap((h) => [h.r + ':' + h.a, h.r + ':' + h.v]));
	const rounds = [...R.keys()].sort((a, b) => a - b);
	for (const r of rounds) {
		const s0 = R.get(r);
		for (let t = 0; t < 2; t++) {
			const mine = s0.ch.filter((c) => c[1] === t && c[7]);
			const foes = s0.ch.filter((c) => c[1] !== t && c[7]);
			for (const c of mine) {
				S[t].aliveRounds++;
				if (!mine.some((o) => o !== c && cheb([o[3], o[4]], [c[3], c[4]]) <= 8)) S[t].loneRounds++;
				if (fightRounds.has(r + ':' + c[0])) {
					S[t].fightBodyRounds++;
					const ml = mine.filter((o) => cheb([o[3], o[4]], [c[3], c[4]]) <= 6).length;
					const fl = foes.filter((o) => cheb([o[3], o[4]], [c[3], c[4]]) <= 6).length;
					if (fl > ml) S[t].fightOutnum++;
				}
			}
		}
	}
	// Respawn walk-outs.
	for (const b of d.meta.bodies) {
		const t = b.team, sp = spawns[t];
		let dead = false, waiting = false;
		for (const r of rounds) {
			const c = R.get(r).ch.find((q) => q[0] === b.index);
			if (!c) continue;
			if (!c[7]) { dead = true; waiting = false; continue; }
			if (dead) { dead = false; waiting = true; }
			if (waiting && !sp.has(c[3] + ',' + c[4])) {
				waiting = false;
				const mates = R.get(r).ch.filter((o) => o[1] === t && o[7] && o[0] !== b.index && cheb([o[3], o[4]], [c[3], c[4]]) <= 4);
				const foesAlive = R.get(r).ch.filter((o) => o[1] !== t && o[7]).length;
				const usAlive = R.get(r).ch.filter((o) => o[1] === t && o[7]).length;
				const died = deaths.some((x) => x.who === b.index && x.primary && x.r > r && x.r <= r + 40);
				const s = S[t];
				s.walkouts++;
				if (foesAlive > usAlive) { s.walkoutsDeficit++; if (!mates.length) s.walkoutsDeficitAlone++; }
				if (!mates.length) { s.walkoutsAlone++; if (died) s.aloneDied++; } else if (died) s.groupDied++;
			}
		}
	}
	return { file, ourTeam, winner, us: S[ourTeam], them: S[1 - ourTeam], meta: { map: path.basename(file), final: d.meta.finalRound, sub: d.meta.submitted } };
}

function report(label, a) {
	const g = Math.max(1, a.games), pd = (x) => (x / g).toFixed(2), pc = (x, n) => (n ? (100 * x / n).toFixed(0) + '%' : '-');
	const cd = Math.max(1, a.champDeaths);
	console.log(`-- ${label}: games ${a.games} wins ${a.wins}`);
	console.log(`   deaths/game ${pd(a.deaths)} (linked ${pd(a.linked)}, by camps ${pd(a.campDeaths)}, by champions ${pd(a.champDeaths)}); bag lost/game ${pd(a.bagLost)}; death cost/game ${pd(a.cost)} gem-eq`);
	console.log(`   champ deaths: alone6 ${pc(a.alone6, cd)} (bag ${pd(a.alone6Bag)}/g, cost ${pd(a.alone6Cost)}/g) | near<=10 no-join ${pc(a.nearNoJoin, cd)} (cost ${pd(a.nearNoJoinCost)}/g) | ` +
		`ally joined ${pc(a.joinedDeaths, cd)} | outnumbered locally, not globally ${pc(a.outnumLocal, cd)} (cost ${pd(a.outnumLocalCost)}/g) | abandoned ${pc(a.abandoned, cd)} (cost ${pd(a.abandonedCost)}/g) | carriers 20+ ${pc(a.carrier20, cd)}`);
	console.log(`   kills/game ${pd(a.kills)}, hitters/kill ${(a.killHitters / Math.max(1, a.kills)).toFixed(2)}, solo kills ${pc(a.soloKills, a.kills)} | multi-hitter rounds/game ${pd(a.multiRounds)}, focused ${pc(a.focusedRounds, a.multiRounds)} | hits/game ${pd(a.hits)}`);
	console.log(`   fights/game ${pd(a.episodes)}: won ${pc(a.epWon, a.episodes)} lost ${pc(a.epLost, a.episodes)} | net kills/fight ${(a.epDiff / Math.max(1, a.episodes)).toFixed(3)} | ` +
		`we fewer ${pc(a.epN_outnum, a.episodes)} (net ${(a.epDiffOutnum / Math.max(1, a.epN_outnum)).toFixed(2)}, lost ${pc(a.epOutnumLost, a.epN_outnum)}, team not outnumbered ${pc(a.epOutnumGlobalOk, a.epN_outnum)}) ` +
		`even ${pc(a.epN_even, a.episodes)} (net ${(a.epDiffEven / Math.max(1, a.epN_even)).toFixed(2)}) more ${pc(a.epN_more, a.episodes)} (net ${(a.epDiffMore / Math.max(1, a.epN_more)).toFixed(2)})`);
	console.log(`   fights with an idle ally within 10: ${pc(a.epIdleNear, a.episodes)} (lost ${pc(a.epIdleNearLost, a.epIdleNear)}) | solo fights ${pc(a.epSolo, a.episodes)} (lost ${pc(a.epSoloLost, a.epSolo)}) | ` +
		`fight body-rounds locally outnumbered ${pc(a.fightOutnum, a.fightBodyRounds)}`);
	console.log(`   walk-outs/game ${pd(a.walkouts)}, alone ${pc(a.walkoutsAlone, a.walkouts)} (died<=40r ${pc(a.aloneDied, a.walkoutsAlone)} vs with ally ${pc(a.groupDied, a.walkouts - a.walkoutsAlone)}); ` +
		`while outnumbered ${pd(a.walkoutsDeficit)}/g, alone ${pc(a.walkoutsDeficitAlone, a.walkoutsDeficit)} | lone body-rounds (no ally within 8) ${pc(a.loneRounds, a.aliveRounds)}`);
}

const args = process.argv.slice(2);
const ji = args.indexOf('--json');
const jsonOut = ji >= 0 ? args.splice(ji, 2)[1] : null;
const si = args.indexOf('--split');
const split = si >= 0 ? (args.splice(si, 1), true) : false;
const files = [];
for (const a of args) {
	if (fs.statSync(a).isDirectory()) for (const f of fs.readdirSync(a)) { if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
	else files.push(a);
}
const byDir = new Map();
const all = [];
for (const f of files.sort()) {
	let res;
	try { res = await analyse(f); } catch (e) { console.error('skip', f, e.message); continue; }
	all.push(res);
	const dir = path.basename(path.dirname(f)).replace(/_\d+$/, '');
	if (!byDir.has(dir)) byDir.set(dir, { us: ZERO(), them: ZERO(), won: ZERO(), lost: ZERO() });
	const b = byDir.get(dir);
	add(b.us, res.us); add(b.them, res.them);
	add(res.winner === res.ourTeam ? b.won : b.lost, res.us);
}
const tot = { us: ZERO(), them: ZERO(), won: ZERO(), lost: ZERO() };
for (const [dir, b] of byDir) {
	console.log(`\n==== ${dir}`);
	report('us', b.us); report('them', b.them);
	if (split) { report('us, games won', b.won); report('us, games lost', b.lost); }
	for (const k of Object.keys(tot)) add(tot[k], b[k]);
}
if (byDir.size > 1) {
	console.log('\n==== all');
	report('us', tot.us); report('them', tot.them);
	if (split) { report('us, games won', tot.won); report('us, games lost', tot.lost); }
}
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(all));
