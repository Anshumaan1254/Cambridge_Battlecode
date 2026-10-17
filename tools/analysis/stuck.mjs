#!/usr/bin/env node
// Stuck-champion detector: finds rounds where a living champion makes no progress (pinned between walls,
// oscillating, or walking without getting closer to its goal), plus rounds lost to fuel rollovers.
//
//   node tools/analysis/stuck.mjs [--team A|B|both] [--worst N] [--json out.json] [--quiet] FILE_OR_DIR...
//
// Input: local `cambc run` bundles (tools/bench.py naming: NAME_B.repl26a = our bot on team B, else A) or raw
// ladder replays. `--team both` analyses both teams. When the bundle holds a LEGEND_TRACE stdout ("T r=.. TYPE
// task=.. g=.. pos=(x,y) ..." per body turn) the champion's task and target group are used too.
//
// A round of a body is "eligible" for stuck detection when it is alive, not on its own spawn, not channelling
// (recall, tribute, crystal teleport, standing on a reward tile it captures), not fighting (no enemy champion
// within 5 tiles this round or last, no fight/flee task in the trace), and did not attack or cast a targeted
// spell (farming a camp is progress). Rounds where it waits next to a respawning group (trace task "wait", or
// within 2 tiles of a group with no live camp and no reward) are counted apart as "wait".
// Episodes, over consecutive eligible rounds:
//   box     the body stays inside a 2x2 box for 6+ rounds (frozen: at most one move; jiggle: more)
//   osc     8+ rounds moving in most of them while staying inside a 3x3 box (A-B-A-B, A-B-C-B-A ...)
//   noprog  (trace only) 10+ rounds with the same task and target, moving in at least half of them, and the
//           walking distance to the goal (target group tiles, spawn, nearest altar) did not shrink
// Also counted: engine "Movement blocked" events (a move into a tile that filled up) and turn rollovers.
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { decode, unwrapReplay, findEngineWasms, CHAMP } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const TASKS = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const T_TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
const DASH_ABILITY = 6;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

export async function mapGrid(replayBuf) {
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
	const wall = new Uint8Array(w * h), hole = new Uint8Array(w * h), altar = new Uint8Array(w * h), bush = new Uint8Array(w * h);
	for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
		const i = y * w + x;
		wall[i] = tile('Game_GetWall', x, y) ? 1 : 0;
		hole[i] = tile('Game_GetHole', x, y) ? 1 : 0;
		altar[i] = tile('Game_GetAltar', x, y) ? 1 : 0;
		bush[i] = tile('Game_GetBush', x, y) ? 1 : 0;
	}
	const mirror = (x, y) => (sym === 0 ? [w - 1 - x, y] : sym === 1 ? [x, h - 1 - y] : [w - 1 - x, h - 1 - y]);
	const spawn = [new Uint8Array(w * h), new Uint8Array(w * h)];
	for (let y = sp[1]; y < sp[3]; y++) for (let x = sp[0]; x < sp[2]; x++) {
		spawn[0][y * w + x] = 1;
		const [mx, my] = mirror(x, y);
		spawn[1][my * w + mx] = 1;
	}
	// Camp groups in engine order (the bot's bc::map::camp_groups() order, which trace g= ids index).
	const camps = [];
	chk(X.Game_GetNumCamps(g, out), 'ncamps');
	const nc = dv().getUint32(out, true);
	const handleTo = new Map();
	for (let j = 0; j < nc; j++) {
		chk(X.Game_GetCampHandle(g, j, out), 'camph');
		const hd = dv().getBigUint64(out, true);
		chk(X.Game_GetCamp(g, hd, out), 'camp');
		const c = { idx: j, type: dv().getInt32(out, true), x: dv().getInt32(out + 4, true), y: dv().getInt32(out + 8, true) };
		camps.push(c);
		handleTo.set(hd, c);
	}
	chk(X.Game_GetNumCampGroups(g, out), 'ngroups');
	const ng = dv().getUint32(out, true);
	const groups = [];
	for (let i = 0; i < ng; i++) {
		chk(X.Game_GetCampGroupHandle(g, i, out), 'grouph');
		const gh = dv().getBigUint64(out, true);
		chk(X.Game_GetCampGroup(g, gh, out), 'group');
		const n = dv().getUint32(out + 12, true);
		const tiles = [];
		for (let k = 0; k < n; k++) {
			chk(X.Game_GetCampGroupCamp(g, gh, k, out), 'gcamp');
			const c = handleTo.get(dv().getBigUint64(out, true));
			if (c) tiles.push([c.x, c.y]), (c.group = i);
		}
		groups.push({ id: i, tiles });
	}
	// The map file holds one half; the game mirrors it. Runtime order (timeline camps and groups, the bot's
	// camp_groups() ids): map camp k -> 2k and its mirror 2k+1; map group i -> 2i and its mirror 2i+1.
	const rcamps = [], rgroups = [];
	for (const c of camps) {
		const [mx, my] = mirror(c.x, c.y);
		rcamps.push({ ...c, idx: rcamps.length, group: c.group * 2 });
		rcamps.push({ ...c, x: mx, y: my, idx: rcamps.length, group: c.group * 2 + 1 });
	}
	for (const g of groups) {
		rgroups.push({ id: rgroups.length, tiles: g.tiles });
		rgroups.push({ id: rgroups.length, tiles: g.tiles.map(([x, y]) => mirror(x, y)) });
	}
	X.Game_Destroy?.(g);
	return { w, h, wall, hole, altar, bush, spawn, groups: rgroups, camps: rcamps };
}

function bfs(grid, blocked, roots) {
	const { w, h } = grid;
	const d = new Int32Array(w * h).fill(1 << 20);
	const q = new Int32Array(w * h);
	let qh = 0, qt = 0;
	for (const [x, y] of roots) { const i = y * w + x; if (i >= 0 && i < w * h && d[i] !== 0) { d[i] = 0; q[qt++] = i; } }
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
	const turns = {};
	let any = false;
	for (let line of text.split('\n')) {
		line = line.replace(/\x00/g, '').trim();
		const m = line.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\)/);
		if (m) {
			any = true;
			const type = T_TYPES[+m[2]];
			(turns[type] ||= {})[+m[1]] = { task: +m[3], g: +m[4], pos: [+m[5], +m[6]] };
		}
	}
	return any ? turns : null;
}

function newAcc() {
	return { cause: {}, games: 0, wins: 0, bodyRounds: 0, alive: 0, eligible: 0, wait: 0, ep: {}, epRounds: {}, blocked: 0, rollovers: 0, rollOpen: 0, perMap: {}, perChamp: {}, worst: [] };
}
const CLASSES = ['frozen', 'jiggle', 'osc', 'noprog'];

function snippet(grid, center, s, ourTeam, bodyIdx, targetTiles, radius = 4) {
	const rows = [];
	const live = new Set();
	if (s) s.campHp.forEach((hp, k) => { if (hp > 0) live.add(grid.camps[k].x + ',' + grid.camps[k].y); });
	const campAt = new Set(grid.camps.map((c) => c.x + ',' + c.y));
	const tgt = new Set((targetTiles || []).map((t) => t[0] + ',' + t[1]));
	const units = new Map();
	if (s) for (const c of s.ch) if (c[7]) units.set(c[3] + ',' + c[4], c[0] === bodyIdx ? '@' : c[1] === ourTeam ? 'a' : 'e');
	for (let y = center[1] - radius; y <= center[1] + radius; y++) {
		let row = '';
		for (let x = center[0] - radius; x <= center[0] + radius; x++) {
			if (x < 0 || y < 0 || x >= grid.w || y >= grid.h) { row += ' '; continue; }
			const i = y * grid.w + x, k = x + ',' + y;
			let ch = '.';
			if (grid.wall[i]) ch = '#';
			else if (grid.hole[i]) ch = 'o';
			else if (grid.altar[i]) ch = 'A';
			else if (units.has(k)) ch = units.get(k);
			else if (campAt.has(k)) ch = tgt.has(k) ? (live.has(k) ? 'T' : 't') : (live.has(k) ? 'C' : 'x');
			else if (grid.spawn[ourTeam][i]) ch = 'S';
			else if (grid.spawn[1 - ourTeam][i]) ch = 'E';
			else if (grid.bush[i]) ch = '"';
			row += ch;
		}
		rows.push(row);
	}
	return rows;
}

async function analyse(file, acc, opts) {
	const raw = fs.readFileSync(file);
	const base = path.basename(file).replace(/\.repl26a$/, '');
	const mapName = base.replace(/_[AB]$/, '');
	const sideB = /_B\.repl26a$/.test(file);
	const teams = opts.team === 'both' ? [0, 1] : opts.team === 'A' ? [0] : opts.team === 'B' ? [1] : [sideB ? 1 : 0];
	const rep = unwrapReplay(raw);
	const d = await decode(rep, { every: 1, rollovers: true });
	const grid = await mapGrid(rep);
	const byRound = new Map();
	for (const r of d.rounds) byRound.set(r.r, r);
	const final = d.meta.finalRound;
	// Per round and body: what happened.
	const ev = new Map(); // "r:who" -> {move, act, actChamp, recall, submit, tp, tpDone, cancel, blocked, roll, banked}
	const get = (r, who) => { const k = r + ':' + who; let o = ev.get(k); if (!o) ev.set(k, (o = {})); return o; };
	const champAt = (r) => { const s = byRound.get(r); return s ? s.ch : []; };
	for (const e of d.events) {
		if (e.who === undefined) continue;
		const o = get(e.r, e.who);
		switch (e.k) {
			case 'Move': o.move = true; break;
			case 'Attack': {
				o.act = true;
				if (e.to) for (const c of champAt(e.r)) if (c[7] && c[1] !== e.team && c[3] === e.to[0] && c[4] === e.to[1]) o.actChamp = true;
				break;
			}
			case 'Cast ability': if (e.ability === DASH_ABILITY) o.move = true; else o.act = true; break;
			case 'Recall': o.recall = true; break;
			case 'Submit gems': o.submit = true; break;
			case 'Banked': o.banked = true; break;
			case 'Teleport channel': o.tp = true; break;
			case 'Teleport complete': o.tpDone = true; break;
			case 'Cancel channel': o.cancel = true; break;
			case 'Movement blocked': o.blocked = true; break;
			case 'Turn rollover': o.roll = true; break;
		}
	}
	const tileGroup = new Map();
	for (const g of grid.groups) for (const t of g.tiles) tileGroup.set(t[0] + ',' + t[1], g.id);
	const campIdxOfGroup = grid.groups.map(() => []);
	grid.camps.forEach((c, k) => { if (c.group !== undefined) campIdxOfGroup[c.group].push(k); });
	const groupLive = (gid, s) => campIdxOfGroup[gid].some((k) => s.campHp[k] > 0);

	for (const team of teams) {
		const text = (() => { try { return unwrapReplay(raw, team ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'); } catch { return ''; } })();
		const trace = parseTrace(text);
		// Static walking fields (walls, holes, altars, the enemy spawn blocked, as the bot's own fields).
		const blocked = new Uint8Array(grid.w * grid.h);
		for (let i = 0; i < blocked.length; i++) blocked[i] = grid.wall[i] | grid.hole[i] | grid.altar[i] | grid.spawn[1 - team][i];
		const fieldCache = new Map();
		const field = (key, roots) => { let f = fieldCache.get(key); if (!f) fieldCache.set(key, (f = bfs(grid, blocked, roots))); return f; };
		const spawnRoots = [];
		for (let i = 0; i < blocked.length; i++) if (grid.spawn[team][i]) spawnRoots.push([i % grid.w, (i / grid.w) | 0]);
		const altarRoots = [];
		for (let i = 0; i < blocked.length; i++) if (grid.altar[i]) {
			const x = i % grid.w, y = (i / grid.w) | 0;
			for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) altarRoots.push([x + dx, y + dy]);
		}
		const goalDist = (t, p) => {
			if (!t) return null;
			const tk = TASKS[t.task];
			const i = p[1] * grid.w + p[0];
			if ((tk === 'farm' || tk === 'capture' || tk === 'wait') && t.g >= 0 && grid.groups[t.g]) return field('g' + t.g, grid.groups[t.g].tiles)[i];
			if (tk === 'home') return field('home', spawnRoots)[i];
			if (tk === 'tribute') return field('altar', altarRoots)[i];
			return null;
		};
		const won = d.meta.outcome === team + 1;
		acc.games++;
		acc.wins += won ? 1 : 0;
		const pm = (acc.perMap[mapName] ||= { games: 0, wins: 0, ep: 0, rounds: 0, roll: 0, blocked: 0 });
		pm.games++;
		pm.wins += won ? 1 : 0;
		const bodies = d.meta.bodies.filter((b) => b.team === team);
		const enemies = d.meta.bodies.filter((b) => b.team !== team).map((b) => b.index);
		const gameEp = { n: 0, rounds: 0 };
		for (const b of bodies) {
			const T = trace ? trace[b.type] || {} : null;
			const pc = (acc.perChamp[b.type] ||= { bodyRounds: 0, ep: 0, rounds: 0, roll: 0, blocked: 0, byClass: {} });
			// Build the per-round series.
			const seq = [];
			let chan = null; // {kind, until}
			let prevPos = null, prevAlive = false, fightPrev = false;
			for (let r = 1; r <= final; r++) {
				const s = byRound.get(r);
				if (!s) continue;
				const c = s.ch.find((q) => q[0] === b.index);
				if (!c) continue;
				const alive = c[7] === 1, pos = [c[3], c[4]];
				const o = ev.get(r + ':' + b.index) || {};
				acc.bodyRounds++;
				pc.bodyRounds++;
				if (o.roll) { acc.rollovers++; pc.roll++; pm.roll++; if (r <= 3) acc.rollOpen++; }
				if (o.blocked) { acc.blocked++; pc.blocked++; pm.blocked++; }
				// Channels.
				if (!alive) chan = null;
				if (o.recall) chan = { kind: 'recall', until: r + 5 };
				if (o.submit) chan = { kind: 'submit', until: r + 12 };
				if (o.tp) chan = { kind: 'tp', until: r + 4 };
				let channel = false;
				if (chan) {
					channel = true;
					if (o.cancel || r > chan.until || (chan.kind === 'submit' && o.banked) || (chan.kind === 'tp' && o.tpDone) ||
						(chan.kind === 'recall' && prevPos && alive && cheb(prevPos, pos) > 2)) chan = null;
					else if (r > (chan.start ?? r) && (o.move || o.act) && !o.recall && !o.submit && !o.tp) { chan = null; channel = false; }
					if (chan && chan.start === undefined) chan.start = r;
				}
				const gid = tileGroup.get(pos[0] + ',' + pos[1]);
				if (alive && gid !== undefined) {
					const prev = byRound.get(r - 1);
					if (s.gr[gid] || (prev && prev.gr[gid])) channel = true; // capturing a reward
				}
				let near = false;
				if (alive) for (const k of enemies) {
					const e = s.ch.find((q) => q[0] === k);
					if (e && e[7] && cheb([e[3], e[4]], pos) <= 5) { near = true; break; }
				}
				const t = T ? T[r] : null;
				const fightTask = t && (t.task === 6 || t.task === 7);
				const fight = near || fightPrev || o.actChamp || fightTask;
				fightPrev = near;
				const onSpawn = alive && grid.spawn[team][pos[1] * grid.w + pos[0]] === 1;
				// Waiting next to a respawning group (by design) is not stuck.
				let wait = false;
				if (alive && !o.act) {
					if (t && t.task === 3 && t.g >= 0 && grid.groups[t.g] && !groupLive(t.g, s) && !s.gr[t.g]) wait = true;
					if (!t) for (const g of grid.groups) {
						if (!g.tiles.some((q) => cheb(q, pos) <= 2)) continue;
						if (!groupLive(g.id, s) && !s.gr[g.id]) { wait = true; break; }
					}
				}
				const moved = alive && prevAlive && prevPos && (pos[0] !== prevPos[0] || pos[1] !== prevPos[1]) && cheb(pos, prevPos) <= 2;
				const elig = alive && !onSpawn && !channel && !fight && !o.act && !wait;
				if (alive) acc.alive++;
				if (elig) acc.eligible++;
				if (alive && wait && !onSpawn && !channel && !fight) acc.wait++;
				seq.push({ r, alive, pos, elig, moved, t, o });
				prevPos = pos;
				prevAlive = alive;
			}
			const homeF = field('home', spawnRoots);
			// A first guess at the cause, from the trace and the surroundings at the episode start.
			const causeOf = (ep, xs) => {
				const ts = xs.filter((x) => x.t).map((x) => x.t);
				const tasks = new Set(ts.map((t) => t.task)), targets = new Set(ts.filter((t) => t.g >= 0).map((t) => t.g));
				const p = xs[0].pos, s0 = byRound.get(xs[0].r);
				const dh = homeF[p[1] * grid.w + p[0]];
				if (tasks.has(5) && tasks.size > 1 && dh <= 4) return 'home-edge';
				if (tasks.size > 1) return 'task-flip';
				if (targets.size > 1) return 'target-flip';
				if (ep.cls === 'noprog') return ep.goalD && ep.goalD[1] - ep.goalD[0] > 8 ? 'walk-away' : 'noprog';
				const g = ts.length && ts[0].g >= 0 ? ts[0].g : -1;
				if (g >= 0 && s0) {
					const ks = campIdxOfGroup[g];
					const dead = ks.filter((k) => s0.campHp[k] <= 0), live = ks.filter((k) => s0.campHp[k] > 0);
					if (dead.length && live.length && dead.some((k) => cheb([grid.camps[k].x, grid.camps[k].y], p) <= 3)) return 'dead-camp';
				}
				if (s0) for (const c of s0.ch) if (c[7] && c[1] === team && c[0] !== b.index && cheb([c[3], c[4]], p) <= 1) return 'ally-adjacent';
				if (s0) for (let k = 0; k < grid.camps.length; k++) if (s0.campHp[k] > 0 && cheb([grid.camps[k].x, grid.camps[k].y], p) <= 1 && grid.camps[k].group !== g) return 'other-camp';
				return ts.length ? 'other' : 'no-trace';
			};
			// Runs of consecutive eligible rounds.
			const flagged = new Uint8Array(seq.length);
			const episodes = [];
			const addEp = (i, j, cls) => {
				for (let k = i; k <= j; k++) flagged[k] = 1;
				const xs = seq.slice(i, j + 1);
				const ep = { file: path.basename(path.dirname(file)).replace(/_\d+$/, '') + '/' + base, map: mapName, team: team ? 'B' : 'A', champ: b.type, idx: b.index, cls, r0: xs[0].r, r1: xs[xs.length - 1].r, len: j - i + 1,
					moves: xs.filter((x) => x.moved).length, blockedEv: xs.filter((x) => x.o.blocked).length,
					pos: xs[0].pos, posEnd: xs[xs.length - 1].pos, task: xs[0].t ? TASKS[xs[0].t.task] + (xs[0].t.g >= 0 ? ' g' + xs[0].t.g : '') : '?',
					tasks: [...new Set(xs.filter((x) => x.t).map((x) => TASKS[x.t.task] + (x.t.g >= 0 ? ':' + x.t.g : '')))].slice(0, 4).join(','),
					tiles: new Set(xs.map((x) => x.pos.join(','))).size };
				if (xs[0].t) { const dg = goalDist(xs[0].t, xs[0].pos); const de = goalDist(xs[0].t, xs[xs.length - 1].pos); ep.goalD = [dg, de]; }
				ep.cause = causeOf(ep, xs);
				ep.snip = snippet(grid, xs[0].pos, byRound.get(xs[0].r), team, b.index, xs[0].t && xs[0].t.g >= 0 && grid.groups[xs[0].t.g] ? grid.groups[xs[0].t.g].tiles : null);
				episodes.push(ep);
			};
			let i = 0;
			while (i < seq.length) {
				if (!seq[i].elig) { i++; continue; }
				let j = i;
				while (j + 1 < seq.length && seq[j + 1].elig) j++;
				// [i..j] is a run. Box episodes (2x2 for 6+ rounds), greedy maximal.
				let a = i;
				while (a <= j) {
					let x0 = seq[a].pos[0], x1 = x0, y0 = seq[a].pos[1], y1 = y0, e = a;
					while (e + 1 <= j) {
						const p = seq[e + 1].pos;
						const nx0 = Math.min(x0, p[0]), nx1 = Math.max(x1, p[0]), ny0 = Math.min(y0, p[1]), ny1 = Math.max(y1, p[1]);
						if (nx1 - nx0 > 1 || ny1 - ny0 > 1) break;
						x0 = nx0, x1 = nx1, y0 = ny0, y1 = ny1, e++;
					}
					if (e - a + 1 >= 6) {
						const mv = seq.slice(a + 1, e + 1).filter((x) => x.moved).length;
						addEp(a, e, mv <= 1 ? 'frozen' : 'jiggle');
						a = e + 1;
					} else a++;
				}
				// Oscillation in a 3x3 box for 8+ rounds, mostly moving.
				a = i;
				while (a <= j) {
					if (flagged[a]) { a++; continue; }
					let x0 = seq[a].pos[0], x1 = x0, y0 = seq[a].pos[1], y1 = y0, e = a;
					while (e + 1 <= j && !flagged[e + 1]) {
						const p = seq[e + 1].pos;
						const nx0 = Math.min(x0, p[0]), nx1 = Math.max(x1, p[0]), ny0 = Math.min(y0, p[1]), ny1 = Math.max(y1, p[1]);
						if (nx1 - nx0 > 2 || ny1 - ny0 > 2) break;
						x0 = nx0, x1 = nx1, y0 = ny0, y1 = ny1, e++;
					}
					const mv = seq.slice(a + 1, e + 1).filter((x) => x.moved).length;
					if (e - a + 1 >= 8 && mv >= 0.6 * (e - a)) {
						addEp(a, e, 'osc');
						a = e + 1;
					} else a++;
				}
				// No progress toward the goal (trace): same task+target for 10+ rounds, moving, distance not shrinking.
				if (T) {
					a = i;
					while (a <= j) {
						if (flagged[a] || !seq[a].t) { a++; continue; }
						const key = seq[a].t.task + ':' + seq[a].t.g;
						const d0 = goalDist(seq[a].t, seq[a].pos);
						if (d0 === null || d0 >= 1 << 20) { a++; continue; }
						let e = a, best = d0;
						while (e + 1 <= j && !flagged[e + 1] && seq[e + 1].t && seq[e + 1].t.task + ':' + seq[e + 1].t.g === key) {
							e++;
							best = Math.min(best, goalDist(seq[e].t, seq[e].pos));
						}
						// Longest prefix [a..k] (k >= a+9) whose distance never went below d0.
						let k = a, kmin = d0;
						for (let q = a + 1; q <= e; q++) { const dq = goalDist(seq[q].t, seq[q].pos); if (dq < d0) break; k = q; kmin = Math.min(kmin, dq); }
						const mv = seq.slice(a + 1, k + 1).filter((x) => x.moved).length;
						if (k - a + 1 >= 10 && mv >= 0.5 * (k - a)) {
							addEp(a, k, 'noprog');
							a = k + 1;
						} else a++;
					}
				}
				i = j + 1;
			}
			for (const ep of episodes) {
				const cz = (acc.cause[ep.cause] ||= { n: 0, rounds: 0 });
				cz.n++;
				cz.rounds += ep.len;
				acc.ep[ep.cls] = (acc.ep[ep.cls] || 0) + 1;
				acc.epRounds[ep.cls] = (acc.epRounds[ep.cls] || 0) + ep.len;
				pc.ep++;
				pc.rounds += ep.len;
				pc.byClass[ep.cls] = (pc.byClass[ep.cls] || 0) + ep.len;
				pm.ep++;
				pm.rounds += ep.len;
				gameEp.n++;
				gameEp.rounds += ep.len;
				acc.worst.push(ep);
			}
			acc.worst.sort((x, y) => y.len - x.len);
			if (acc.worst.length > 200) acc.worst.length = 200;
		}
		if (!opts.quiet) {
			const gems = d.meta.submitted;
			console.log(`${(base + (opts.team === 'both' ? ' t' + 'AB'[team] : '')).padEnd(36)} ${won ? 'W' : 'L'} r=${String(final).padStart(4)} ${gems[team]}-${gems[1 - team]} trace=${trace ? 'y' : 'n'} stuck=${gameEp.n} eps ${gameEp.rounds} rounds`);
		}
	}
}

export function report(acc, worstN = 15) {
	const lines = [];
	const tot = Object.values(acc.epRounds).reduce((a, b) => a + b, 0);
	const n = Object.values(acc.ep).reduce((a, b) => a + b, 0);
	lines.push(`== ${acc.games} games (won ${acc.wins}), ${acc.bodyRounds} body-rounds, alive ${acc.alive}, eligible ${acc.eligible} (${(100 * acc.eligible / Math.max(1, acc.alive)).toFixed(1)}% of alive), waiting by a respawn ${acc.wait}`);
	lines.push(`stuck episodes ${n}, ${tot} body-rounds (${(1000 * tot / Math.max(1, acc.alive)).toFixed(2)} per 1000 alive body-rounds, ${(tot / Math.max(1, acc.games)).toFixed(1)} per game): ` +
		CLASSES.map((c) => `${c} ${acc.ep[c] || 0}/${acc.epRounds[c] || 0}r`).join(', '));
	lines.push('by cause (episodes/rounds): ' + Object.entries(acc.cause).sort((a, b) => b[1].rounds - a[1].rounds).map(([k, v]) => `${k} ${v.n}/${v.rounds}r`).join(', '));
	lines.push(`movement-blocked events ${acc.blocked} (${(acc.blocked / Math.max(1, acc.games)).toFixed(2)}/game); turn rollovers ${acc.rollovers} (${(acc.rollovers / Math.max(1, acc.games)).toFixed(2)}/game, ${acc.rollOpen} in rounds 1-3)`);
	lines.push('per map (games, episodes, stuck rounds, rollovers, blocked):');
	for (const [m, v] of Object.entries(acc.perMap).sort((a, b) => b[1].rounds - a[1].rounds))
		if (v.rounds || v.roll > v.games * 12 || v.blocked) lines.push(`  ${m.padEnd(30)} ${v.games}g W${v.wins} ep=${v.ep} rounds=${v.rounds} roll=${v.roll} blocked=${v.blocked}`);
	lines.push('per champion (episodes, stuck rounds per 1000 body-rounds, by class, rollovers):');
	for (const [c, v] of Object.entries(acc.perChamp).sort((a, b) => b[1].rounds - a[1].rounds))
		lines.push(`  ${c.padEnd(10)} ep=${v.ep} rounds=${v.rounds} (${(1000 * v.rounds / Math.max(1, v.bodyRounds)).toFixed(2)}/1000) ` +
			CLASSES.filter((k) => v.byClass[k]).map((k) => `${k}=${v.byClass[k]}`).join(' ') + ` roll=${v.roll} blocked=${v.blocked}`);
	lines.push(`worst episodes:`);
	for (const ep of acc.worst.slice(0, worstN)) {
		lines.push(`  ${ep.file} ${ep.team} ${ep.champ} ${ep.cls} r${ep.r0}-${ep.r1} (${ep.len}) at (${ep.pos}) -> (${ep.posEnd}) moves=${ep.moves} tiles=${ep.tiles} blocked=${ep.blockedEv} cause=${ep.cause} task=${ep.tasks || ep.task}` +
			(ep.goalD ? ` goalD ${ep.goalD[0]}->${ep.goalD[1]}` : ''));
		for (const row of ep.snip) lines.push('      ' + row);
	}
	return lines.join('\n');
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('stuck.mjs')) {
	const argv = process.argv.slice(2);
	const opts = { team: 'auto', worst: 15, json: null, quiet: false };
	const files = [];
	for (let i = 0; i < argv.length; i++) {
		const a = argv[i];
		if (a === '--team') { opts.team = argv[++i]; continue; }
		if (a === '--worst') { opts.worst = +argv[++i]; continue; }
		if (a === '--json') { opts.json = argv[++i]; continue; }
		if (a === '--quiet') { opts.quiet = true; continue; }
		if (fs.statSync(a).isDirectory()) { for (const f of fs.readdirSync(a).sort()) if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
		else files.push(a);
	}
	const acc = newAcc();
	for (const f of files) {
		try { await analyse(f, acc, opts); } catch (e) { console.log(f, 'FAILED', e.stack); }
	}
	console.log(report(acc, opts.worst));
	if (opts.json) fs.writeFileSync(opts.json, JSON.stringify(acc));
}
