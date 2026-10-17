#!/usr/bin/env node
// Route / time-use analysis of our bodies from LEGEND_TRACE replay bundles (local `cambc run` zips).
//
//   node tools/analysis/route_stats.mjs [--json out.json] FILE_OR_DIR...
//
// A bundle NAME_B.repl26a (tools/bench.py naming) is read as our bot on team B, anything else as team A.
// Needs the trace lines the _x_route trace build prints: "M ..." + "G id=.. tiles=x,y;..." once per team,
// "T r=.. TYPE task=.. g=.. pos=(x,y) ..." per body turn. Positions, attacks, captures and deaths come from
// the decoded replay; walking distances from an offline 8-neighbour BFS over the map (walls, holes, altars
// and the enemy spawn blocked, like the bot's own fields).
//
// Reports per game and in total:
//   time share of alive body-rounds: walk (moving toward a camp task), hit, capture, wait, bank, home, fight...
//   walking steps per collected gem, idle rounds
//   duplicate walks (two bodies walking to the same group), crossing paths (swapping targets saves steps),
//   abandoned walks (switched target before arriving), 2-opt order regret on consecutive farm targets.
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { decode, unwrapReplay, findEngineWasms, CHAMP } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const TASKS = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const T_TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

async function mapGrid(replayBuf) {
	const wasi = new WASI({ version: 'preview1', args: [], env: {} });
	const mod = await WebAssembly.compile(fs.readFileSync(findEngineWasms()[0]));
	const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
	wasi.initialize(inst);
	const X = inst.exports, out = X.Engine_Malloc(64), dv = () => new DataView(X.memory.buffer);
	const chk = (r, w) => { if (r !== 0) throw new Error(w + ' ' + r); };
	const p = X.Engine_Malloc(replayBuf.length);
	new Uint8Array(X.memory.buffer, p, replayBuf.length).set(replayBuf);
	chk(X.Game_FromReplayFileBytes(p, replayBuf.length, out), 'load');
	const g = dv().getBigUint64(out, true);
	chk(X.Game_GetBitboardMetadata(g, out), 'meta');
	const w = dv().getInt32(out, true), h = dv().getInt32(out + 4, true);
	chk(X.Game_GetSymmetry(g, out), 'sym');
	const sym = dv().getInt32(out, true);
	chk(X.Game_GetTeamASpawnArea(g, out), 'spawn');
	const sp = [0, 4, 8, 12].map((o) => dv().getInt32(out + o, true));
	const tile = (fn, x, y) => { chk(X[fn](g, x, y, out), fn); return dv().getUint8(out) !== 0; };
	const block = new Uint8Array(w * h); // 1 terrain/altar
	for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
		if (tile('Game_GetWall', x, y) || tile('Game_GetHole', x, y) || tile('Game_GetAltar', x, y)) block[y * w + x] = 1;
	const mirror = (x, y) => (sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y]);
	const spawnA = new Uint8Array(w * h), spawnB = new Uint8Array(w * h);
	for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) {
		spawnA[y * w + x] = 1;
		const [mx, my] = mirror(x, y);
		spawnB[my * w + mx] = 1;
	}
	return { w, h, block, spawnA, spawnB };
}

function bfs(grid, blocked, roots) {
	const { w, h } = grid;
	const d = new Int32Array(w * h).fill(1 << 20);
	const q = new Int32Array(w * h);
	let qh = 0, qt = 0;
	for (const [x, y] of roots) { const i = y * w + x; if (d[i] !== 0) { d[i] = 0; q[qt++] = i; } }
	while (qh < qt) {
		const i = q[qh++], x = i % w, y = (i / w) | 0;
		for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
			if (!dx && !dy) continue;
			const nx = x + dx, ny = y + dy;
			if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
			const j = ny * w + nx;
			if (blocked[j] || d[j] <= d[i] + 1) continue;
			d[j] = d[i] + 1;
			q[qt++] = j;
		}
	}
	return d;
}

function parseTrace(text) {
	const groups = [], turns = {};
	let team = null;
	for (let line of text.split('\n')) {
		line = line.replace(/\x00/g, '').trim();
		let m = line.match(/^M w=(\d+) h=(\d+) spawn=\((\d+),(\d+)\) team=(\d+)/);
		if (m) { team = +m[5]; continue; }
		m = line.match(/^G id=(\d+) gems=(\d+) gold=(\d+) respawn=(\d+) ours=(\d) d_ally=(\d+) hp=\s*(\d+) tiles=(.*)$/);
		if (m) {
			const tiles = m[8].split(';').filter(Boolean).map((s) => s.split(',').map(Number));
			groups[+m[1]] = { id: +m[1], gems: +m[2], gold: +m[3], respawn: +m[4], ours: +m[5], d_ally: +m[6], hp: +m[7], tiles };
			continue;
		}
		m = line.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\) hp=(\d+) gems=(\d+) gold=(\d+)/);
		if (m) {
			const type = T_TYPES[+m[2]];
			(turns[type] ||= {})[+m[1]] = { task: +m[3], g: +m[4], pos: [+m[5], +m[6]], gems: +m[8], gold: +m[9] };
		}
	}
	return { groups, turns, team };
}

function newAcc() {
	return {
		games: 0, bodyRounds: 0, dead: 0, alive: 0, cat: {}, steps: 0, farmSteps: 0, gems: 0, gold: 0, banked: 0, captures: 0,
		dupRounds: 0, walkRounds: 0, crossPairs: 0, crossSave: 0, abandoned: 0, abandonedSteps: 0, segments: 0,
		walkProgress: 0, walkMeasured: 0, walkNoTarget: 0, osc: {}, oscTurns: 0, turns: 0, crossNear: 0, crossNearSave: 0,
		pairs: 0, regretPairs: 0, regretSteps: 0, chainWalk: 0, firstWalk: 0, nextWalk: [], winRound: [], longWalkSteps: 0,
	};
}

async function analyse(file, acc) {
	const raw = fs.readFileSync(file);
	const ourTeam = /_B\.repl26a$/.test(file) ? 1 : 0;
	const text = unwrapReplay(raw, ourTeam ? 'team-b.stdout' : 'team-a.stdout').toString('latin1');
	const tr = parseTrace(text);
	if (!tr.groups.length) { console.log(file, 'no trace'); return; }
	const rep = unwrapReplay(raw);
	const d = await decode(rep, { every: 1 });
	const grid = await mapGrid(rep);
	const blocked = new Uint8Array(grid.w * grid.h);
	const enemySpawn = ourTeam ? grid.spawnA : grid.spawnB;
	const ourSpawn = ourTeam ? grid.spawnB : grid.spawnA;
	for (let i = 0; i < blocked.length; i++) blocked[i] = grid.block[i] || enemySpawn[i];
	const G = tr.groups;
	const gfield = G.map((g) => bfs(grid, blocked, g.tiles));
	const gd = (gid, p) => gfield[gid][p[1] * grid.w + p[0]];
	const tileGroup = new Map();
	for (const g of G) for (const t of g.tiles) tileGroup.set(t[0] + ',' + t[1], g.id);
	// Group availability per round from camp health (alive = some camp has health).
	const campGroup = d.meta.camps.map((c) => tileGroup.get(c.x + ',' + c.y) ?? -1);
	const byRound = new Map();
	for (const r of d.rounds) byRound.set(r.r, r);
	const final = d.meta.finalRound;
	const galive = (gid, r) => {
		const s = byRound.get(r);
		if (!s) return false;
		for (let k = 0; k < campGroup.length; k++) if (campGroup[k] === gid && s.campHp[k] > 0) return true;
		return false;
	};
	const bodies = d.meta.bodies.filter((b) => b.team === ourTeam);
	const attacksCamp = new Set(); // "r:who" attacked a camp tile
	for (const e of d.events) if (e.k === 'Attack' && e.who !== undefined && e.to && tileGroup.has(e.to[0] + ',' + e.to[1])) attacksCamp.add(e.r + ':' + e.who);
	const banked = d.events.filter((e) => e.k === 'Banked' && e.team === ourTeam).reduce((s, e) => s + e.gems, 0);
	const chanUntil = {}; // who -> round until which a recall / submit channel runs
	const chan = new Map();
	for (const e of d.events) if ((e.k === 'Recall' || e.k === 'Submit gems') && e.team === ourTeam) chan.set(e.r + ':' + e.who, e.k);
	acc.games++;
	acc.banked += banked;
	const sub = d.meta.submitted[ourTeam];
	const won = sub >= 1000;
	if (won) acc.winRound.push(final);
	const game = { file: path.basename(file), final, sub, them: d.meta.submitted[1 - ourTeam], cat: {}, steps: 0, gems: 0 };
	const per = {}; // per body: arrays per round
	for (const b of bodies) {
		const T = tr.turns[b.type] || {};
		const seq = [];
		let prevPos = null, prevAlive = false, chanKind = null, chanLeft = 0;
		for (let r = 1; r <= final; r++) {
			const s = byRound.get(r);
			if (!s) continue;
			const c = s.ch.find((q) => q[0] === b.index);
			const alive = c[7] === 1, pos = [c[3], c[4]];
			acc.bodyRounds++;
			let cat;
			const t = T[r];
			const mv = prevAlive && alive && prevPos ? cheb(pos, prevPos) : 0;
			const step = mv <= 2 ? mv : 0; // larger jumps are recalls / teleports / respawns
			const ck = chan.get(r + ':' + b.index);
			if (ck) chanKind = ck, chanLeft = ck === 'Recall' ? 5 : 4;
			if (!alive) cat = 'dead';
			else if (t) {
				const tk = TASKS[t.task];
				if ((tk === 'farm' || tk === 'wait' || tk === 'capture') && t.g >= 0) {
					if (attacksCamp.has(r + ':' + b.index)) cat = 'hit';
					else if (step > 0) cat = 'walk';
					else cat = tk === 'farm' ? 'hit-idle' : tk;
				} else if (tk === 'home') cat = step > 0 ? 'home-walk' : 'home-rest';
				else if (tk === 'tribute') cat = 'bank';
				else cat = tk;
				chanLeft = 0;
			} else if (chanLeft > 0) cat = chanKind === 'Recall' ? 'recall' : 'bank', chanLeft--;
			else cat = 'noturn';
			if (alive) acc.alive++;
			acc.cat[cat] = (acc.cat[cat] || 0) + 1;
			game.cat[cat] = (game.cat[cat] || 0) + 1;
			acc.steps += step;
			game.steps += step;
			if (cat === 'walk') acc.farmSteps += step;
			// Captures: gems or gold gained while standing on a camp tile.
			if (prevAlive && alive && seq.length) {
				const o = seq[seq.length - 1];
				const onTile = tileGroup.has(pos[0] + ',' + pos[1]) || tileGroup.has(o.pos[0] + ',' + o.pos[1]);
				if (c[8] > o.gems) acc.gems += c[8] - o.gems, game.gems += c[8] - o.gems;
				if ((c[8] > o.gems || c[9] > o.gold + 10) && onTile) acc.captures++, seq[seq.length - 1].capAfter = true;
			}
			seq.push({ r, pos, alive, cat, t, step, gems: c[8], gold: c[9] });
			prevPos = pos;
			prevAlive = alive;
		}
		per[b.index] = seq;
	}
	// Segments: consecutive turns with the same target group under farm/wait/capture tasks.
	for (const b of bodies) {
		const seq = per[b.index];
		const segs = [];
		let cur = null;
		for (const x of seq) {
			const tk = x.t ? TASKS[x.t.task] : null;
			const g = x.t && (tk === 'farm' || tk === 'wait' || tk === 'capture') ? x.t.g : -1;
			if (g >= 0 && cur && cur.g === g && x.r - cur.end <= 2) {
				cur.end = x.r;
				cur.steps += x.step;
				cur.minD = Math.min(cur.minD, gd(g, x.pos));
				cur.lastPos = x.pos;
				if (x.cat === 'hit') cur.hit = true;
				if (x.capAfter) cur.cap = true;
				continue;
			}
			if (g >= 0) {
				// Where we stood when we chose it: the position before this turn's move.
				const prev = seq[seq.indexOf(x) - 1];
				const p0 = prev && prev.alive ? prev.pos : x.pos;
				cur = { g, start: x.r, end: x.r, p0, d0: gd(g, p0), steps: x.step, minD: gd(g, x.pos), lastPos: x.pos, hit: x.cat === 'hit', cap: !!x.capAfter, nextTask: null };
				segs.push(cur);
			} else {
				if (cur && cur.nextTask === null) cur.nextTask = tk || x.cat;
				cur = null;
			}
		}
		acc.segments += segs.length;
		for (let i = 0; i < segs.length; i++) {
			const s = segs[i];
			if (s.minD >= 3 && i + 1 < segs.length && segs[i + 1].start - s.end <= 2 && segs[i + 1].g !== s.g) {
				acc.abandoned++;
				acc.abandonedSteps += s.steps;
			}
			if (s.d0 > 20) acc.longWalkSteps += Math.min(s.steps, s.d0);
		}
		// Consecutive reached targets (hit or captured) with no other task in between: 2-opt order regret.
		const reached = segs.filter((s) => s.minD <= 3 && (s.hit || s.cap));
		// Hindsight path efficiency: each walking step toward a camp target, measured against the next group
		// this body actually reached (hit or captured). Detours, flip-flops and abandoned walks show up as waste.
		{
			let k = 0;
			for (let i = 1; i < seq.length; i++) {
				const x = seq[i], pv = seq[i - 1];
				if (x.cat !== 'walk' || !pv.alive) continue;
				while (k < reached.length && reached[k].end < x.r) k++;
				if (k >= reached.length) { acc.walkNoTarget += x.step; continue; }
				const g = reached[k].g;
				acc.walkProgress += gd(g, pv.pos) - gd(g, x.pos);
				acc.walkMeasured += x.step;
			}
		}
		// Oscillation: A-B-A-B alternation of (task, group) over four turns within five rounds.
		{
			const ts = seq.filter((x) => x.t);
			const fl = new Uint8Array(ts.length);
			for (let i = 3; i < ts.length; i++) {
				if (ts[i].r - ts[i - 3].r > 4) continue;
				const key = (x) => x.t.task + ':' + x.t.g;
				if (key(ts[i - 3]) === key(ts[i - 1]) && key(ts[i - 2]) === key(ts[i]) && key(ts[i]) !== key(ts[i - 1])) fl[i - 3] = fl[i - 2] = fl[i - 1] = fl[i] = 1;
			}
			for (let i = 0; i < ts.length; i++) if (fl[i]) {
				const a = ts[Math.max(0, i - 1)].t, b = ts[i].t;
				const kind = a.task === b.task ? 'switch-g(' + TASKS[b.task] + ')' : [TASKS[a.task], TASKS[b.task]].sort().join('<->');
				acc.osc[kind] = (acc.osc[kind] || 0) + 1;
				acc.oscTurns++;
			}
			acc.turns += ts.length;
		}
		for (let i = 0; i + 1 < reached.length; i++) {
			const A = reached[i], B = reached[i + 1];
			if (B.start - A.end > 3 || A.g === B.g) continue;
			if (segs.indexOf(B) !== segs.indexOf(A) + 1) continue;
			acc.pairs++;
			const walkAB = gd(B.g, A.lastPos);
			acc.chainWalk += walkAB;
			acc.nextWalk.push(walkAB);
			acc.firstWalk += A.d0;
			const actual = A.d0 + walkAB;
			// The other order: B first, then A (from B's tiles).
			const bToA = Math.min(...G[B.g].tiles.map((t) => gd(A.g, t)));
			const swapped = gd(B.g, A.p0) + bToA;
			if (galive(B.g, A.start) && actual - swapped >= 5) {
				acc.regretPairs++;
				acc.regretSteps += actual - swapped;
			}
		}
	}
	// Team: duplicate walks and crossing paths, per round.
	const seen = new Set();
	for (let r = 1; r <= final; r++) {
		const walkers = [];
		for (const b of bodies) {
			const x = per[b.index].find((q) => q.r === r);
			if (x && x.cat === 'walk' && x.t) walkers.push({ who: b.index, g: x.t.g, pos: x.pos });
		}
		acc.walkRounds += walkers.length;
		for (let i = 0; i < walkers.length; i++) for (let j = i + 1; j < walkers.length; j++) {
			const a = walkers[i], c = walkers[j];
			if (a.g === c.g) {
				if (gd(a.g, a.pos) > 3 && gd(c.g, c.pos) > 3) acc.dupRounds += 2;
				continue;
			}
			const now = gd(a.g, a.pos) + gd(c.g, c.pos), sw = gd(c.g, a.pos) + gd(a.g, c.pos);
			const key = [a.who, c.who, a.g, c.g].join(':');
			if (now - sw >= 6 && !seen.has(key)) {
				seen.add(key); acc.crossPairs++; acc.crossSave += now - sw;
				if (cheb(a.pos, c.pos) <= 7) acc.crossNear++, acc.crossNearSave += now - sw; // in sight of each other
			}
		}
	}
	const alive = Object.entries(game.cat).filter(([k]) => k !== 'dead').reduce((s, [, v]) => s + v, 0);
	console.log(`${game.file.padEnd(34)} r=${String(final).padStart(4)} ${sub}-${game.them} steps=${game.steps} gems=${game.gems} steps/gem=${(game.steps / Math.max(1, game.gems)).toFixed(2)} ` +
		['walk', 'hit', 'capture', 'wait', 'bank', 'recall', 'home-walk', 'home-rest', 'fight', 'flee'].map((k) => `${k}=${(100 * (game.cat[k] || 0) / Math.max(1, alive)).toFixed(0)}%`).join(' '));
}

const argv = process.argv.slice(2);
let jsonOut = null;
const files = [];
for (let i = 0; i < argv.length; i++) {
	if (argv[i] === '--json') { jsonOut = argv[++i]; continue; }
	const p = argv[i];
	if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p).sort()) { if (f.endsWith('.repl26a')) files.push(path.join(p, f)); }
	else files.push(p);
}
const acc = newAcc();
for (const f of files) {
	try { await analyse(f, acc); } catch (e) { console.log(f, 'FAILED', e.message); }
}
const pct = (k) => (100 * (acc.cat[k] || 0) / Math.max(1, acc.alive)).toFixed(1);
console.log(`\n== ${acc.games} games, ${acc.bodyRounds} body-rounds, dead ${(100 * (acc.cat.dead || 0) / acc.bodyRounds).toFixed(1)}%`);
console.log('share of alive body-rounds: ' + Object.keys(acc.cat).filter((k) => k !== 'dead').sort((a, b) => acc.cat[b] - acc.cat[a]).map((k) => `${k}=${pct(k)}%`).join(' '));
console.log(`walking steps ${acc.steps} (to camp targets ${acc.farmSteps}); gems collected ${acc.gems}, banked ${acc.banked}; steps/gem ${(acc.steps / Math.max(1, acc.gems)).toFixed(2)} (camp walks ${(acc.farmSteps / Math.max(1, acc.gems)).toFixed(2)}); captures ${acc.captures}`);
console.log(`walks toward targets >20 steps away: ${acc.longWalkSteps} steps (${(100 * acc.longWalkSteps / Math.max(1, acc.farmSteps)).toFixed(1)}% of camp walking)`);
console.log(`duplicate walks (two bodies walking to the same group, both >3 away): ${acc.dupRounds} of ${acc.walkRounds} walking body-rounds (${(100 * acc.dupRounds / Math.max(1, acc.walkRounds)).toFixed(1)}%)`);
console.log(`crossing paths (swap of two walkers' targets saves >=6 steps): ${acc.crossPairs} pairs, ${acc.crossSave} steps (${(100 * acc.crossSave / Math.max(1, acc.farmSteps)).toFixed(1)}% of camp walking)`);
console.log(`  of which the two walkers were within 7 tiles (could see each other): ${acc.crossNear} pairs, ${acc.crossNearSave} steps`);
console.log(`hindsight path efficiency of camp walks (progress toward the next group actually reached / steps): ${(100 * acc.walkProgress / Math.max(1, acc.walkMeasured)).toFixed(1)}% of ${acc.walkMeasured} steps; ${acc.walkNoTarget} steps with no later target`);
console.log(`oscillating turns (A-B-A-B task/target): ${acc.oscTurns} of ${acc.turns} (${(100 * acc.oscTurns / Math.max(1, acc.turns)).toFixed(1)}%): ` + Object.entries(acc.osc).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => `${k}=${v}`).join(' '));
console.log(`target segments ${acc.segments}; abandoned before arrival then switched: ${acc.abandoned} (${acc.abandonedSteps} steps = ${(100 * acc.abandonedSteps / Math.max(1, acc.farmSteps)).toFixed(1)}% of camp walking)`);
const nw = acc.nextWalk.slice().sort((a, b) => a - b);
const q = (f) => nw.length ? nw[Math.min(nw.length - 1, Math.floor(f * nw.length))] : 0;
console.log(`consecutive farm targets: ${acc.pairs} pairs; walk to the first ${(acc.firstWalk / Math.max(1, acc.pairs)).toFixed(1)}, A->B walk mean ${(acc.chainWalk / Math.max(1, acc.pairs)).toFixed(1)} median ${q(0.5)} p90 ${q(0.9)}`);
console.log(`2-opt order regret (B alive at decision, B-first saves >=5): ${acc.regretPairs} pairs (${(100 * acc.regretPairs / Math.max(1, acc.pairs)).toFixed(1)}%), ${acc.regretSteps} steps (${(100 * acc.regretSteps / Math.max(1, acc.farmSteps)).toFixed(1)}% of camp walking)`);
if (acc.winRound.length) console.log(`wins ${acc.winRound.length}, mean win round ${(acc.winRound.reduce((a, b) => a + b, 0) / acc.winRound.length).toFixed(0)}`);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(acc));
