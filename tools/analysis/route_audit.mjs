#!/usr/bin/env node
// Decision-point audit of our farm routes from LEGEND_TRACE replay bundles (complements route_stats.mjs).
//
//   node tools/analysis/route_audit.mjs FILE_OR_DIR...
//
// Needs the "M"/"G"/"T" trace lines of the _x_route trace build (see route_stats.mjs). A bundle NAME_B.repl26a
// is read as our bot on team B. Walking distances come from an offline 8-neighbour BFS (walls, holes, altars
// and the enemy spawn blocked, like the bot's fields); group state from the decoded camp health.
//
// For every new farm/wait/capture target a body picks it reports:
//   the walk to it, whether a nearer live group nobody of ours targeted was skipped (and by how much),
//   whether the target was still respawning, and what a one-step lookahead would have changed: the best
//   follow-up group after the chosen one, against the best (g1, g2) pair by combined gems per round.
//   The lookahead model is crude (a fixed 8 rounds of work per group, kill time and danger ignored): it
//   shows how often a pair-wise choice differs, not what it would gain in a game.
// Per game it also reports group coverage: gem-weighted rounds that live, untouched groups waited with no
// body of ours within 3 tiles (unfarmed supply), split by our half / their half.
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import { decode, unwrapReplay, findEngineWasms } from '../replay/decode.mjs';

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
	const block = new Uint8Array(w * h);
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
	for (let line of text.split('\n')) {
		line = line.replace(/\x00/g, '').trim();
		let m = line.match(/^G id=(\d+) gems=(\d+) gold=(\d+) respawn=(\d+) ours=(\d) d_ally=(\d+) hp=\s*(\d+) tiles=(.*)$/);
		if (m) {
			const tiles = m[8].split(';').filter(Boolean).map((s) => s.split(',').map(Number));
			groups[+m[1]] = { id: +m[1], gems: +m[2], gold: +m[3], respawn: +m[4], ours: +m[5], d_ally: +m[6], hp: +m[7], tiles };
			continue;
		}
		m = line.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\)/);
		if (m) (turns[T_TYPES[+m[2]]] ||= {})[+m[1]] = { task: +m[3], g: +m[4], pos: [+m[5], +m[6]] };
	}
	return { groups, turns };
}

const acc = { games: 0, decisions: 0, captureDec: 0, walk: 0, longDec: 0, longWalk: 0, skipped: 0, skippedSteps: 0, skippedLong: 0, respawnTarget: 0,
	noneNear: 0, la: 0, laChange: 0, laGain: 0, laD12: 0, laD12best: 0, cover: [0, 0], coverAll: [0, 0], depleted: 0, depletedRounds: 0, roundsAll: 0 };

async function analyse(file) {
	const raw = fs.readFileSync(file);
	const ourTeam = /_B\.repl26a$/.test(file) ? 1 : 0;
	const tr = parseTrace(unwrapReplay(raw, ourTeam ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'));
	if (!tr.groups.length) { console.log(file, 'no trace'); return; }
	const rep = unwrapReplay(raw);
	const d = await decode(rep, { every: 1 });
	const grid = await mapGrid(rep);
	const blocked = new Uint8Array(grid.w * grid.h);
	const enemySpawn = ourTeam ? grid.spawnA : grid.spawnB;
	for (let i = 0; i < blocked.length; i++) blocked[i] = grid.block[i] || enemySpawn[i];
	const G = tr.groups;
	const gfield = G.map((g) => bfs(grid, blocked, g.tiles));
	const gd = (gid, p) => gfield[gid][p[1] * grid.w + p[0]];
	// group-to-group walking distance (from any tile of a to the nearest tile of b)
	const gg = G.map((a) => G.map((b) => Math.min(...a.tiles.map((t) => gd(b.id, t)))));
	const tileGroup = new Map();
	for (const g of G) for (const t of g.tiles) tileGroup.set(t[0] + ',' + t[1], g.id);
	const campGroup = d.meta.camps.map((c) => tileGroup.get(c.x + ',' + c.y) ?? -1);
	const maxHp = new Map();
	const byRound = new Map();
	for (const r of d.rounds) byRound.set(r.r, r);
	const final = d.meta.finalRound;
	// per round: group alive (some camp hp>0), untouched (all camps at their max seen hp)
	const gstate = (gid, r) => {
		const s = byRound.get(r);
		if (!s) return 0;
		let alive = false, full = true;
		for (let k = 0; k < campGroup.length; k++) if (campGroup[k] === gid) {
			const hp = s.campHp[k];
			const mx = Math.max(maxHp.get(k) || 0, hp);
			maxHp.set(k, mx);
			if (hp > 0) alive = true;
			if (hp < mx) full = false;
		}
		return alive ? (full ? 2 : 1) : 0;
	};
	for (const r of d.rounds) for (let k = 0; k < campGroup.length; k++) maxHp.set(k, Math.max(maxHp.get(k) || 0, r.campHp[k]));
	const bodies = d.meta.bodies.filter((b) => b.team === ourTeam);
	const posAt = (b, r) => { const s = byRound.get(r); const c = s && s.ch.find((q) => q[0] === b.index); return c && c[7] === 1 ? [c[3], c[4]] : null; };
	const value = (g) => G[g].gems + 0.22 * G[g].gold;
	acc.games++;
	let gDec = 0, gSkip = 0, gLa = 0, gLaChange = 0;
	// Decision points
	for (const b of bodies) {
		const T = tr.turns[b.type] || {};
		let prevG = -1;
		for (let r = 2; r <= final; r++) {
			const t = T[r];
			const tk = t ? TASKS[t.task] : null;
			const g = t && (tk === 'farm' || tk === 'wait' || tk === 'capture') ? t.g : -1;
			if (g >= 0 && g !== prevG) {
				const p0 = posAt(b, r - 1) || t.pos;
				const d0 = gd(g, p0);
				// targets of our other bodies at this moment
				const taken = new Set();
				for (const o of bodies) if (o !== b) {
					const ot = (tr.turns[o.type] || {})[r - 1] || (tr.turns[o.type] || {})[r];
					if (ot && ot.task >= 1 && ot.task <= 3 && ot.g >= 0) taken.add(ot.g);
				}
				acc.decisions++; gDec++;
				acc.walk += d0;
				const st = gstate(g, r - 1);
				if (st === 0 && tk !== 'capture') acc.respawnTarget++;
				if (tk === 'capture') acc.captureDec++;
				let dn = 1 << 20, gn = -1;
				for (const h of G) if (h.id !== g && !taken.has(h.id) && gstate(h.id, r - 1) > 0 && gd(h.id, p0) < dn) dn = gd(h.id, p0), gn = h.id;
				if (gn >= 0 && dn + 5 < d0) {
					acc.skipped++; gSkip++;
					acc.skippedSteps += d0 - dn;
					if (d0 > 20) acc.skippedLong++;
				}
				if (gn < 0 || dn > 20) acc.noneNear++;
				if (d0 > 20) acc.longDec++, acc.longWalk += d0;
				// One-step lookahead with the same simple model for every pair: gems per round of (g1 then g2),
				// work = 8 rounds per group (kill + capture, typical), groups alive now and not taken.
				const cand = G.filter((h) => !taken.has(h.id) && (gstate(h.id, r - 1) > 0 || h.id === g)).map((h) => h.id);
				if (cand.length >= 2 && st > 0) {
					const W1 = 8;
					const rate1 = (a) => value(a) / (gd(a, p0) + W1);
					const pair = (a) => {
						let best = 0, bb = -1;
						for (const c of cand) if (c !== a) {
							const v = (value(a) + value(c)) / (gd(a, p0) + W1 + gg[a][c] + W1);
							if (v > best) best = v, bb = c;
						}
						return [best, bb];
					};
					// greedy by the simple model, and best by pair
					let gA = -1, rA = -1;
					for (const a of cand) if (rate1(a) > rA) rA = rate1(a), gA = a;
					let gB = -1, rB = -1, d12 = 0;
					for (const a of cand) { const [v, c] = pair(a); if (v > rB) rB = v, gB = a, d12 = gg[a][c]; }
					const [vA, cA] = pair(gA);
					acc.la++; gLa++;
					acc.laD12 += gg[gA][cA]; acc.laD12best += d12;
					if (gB !== gA) { acc.laChange++; gLaChange++; acc.laGain += rB / Math.max(1e-9, vA) - 1; }
				}
			}
			prevG = g >= 0 ? g : (t ? -1 : prevG);
		}
	}
	// Coverage: live untouched groups with no body of ours within 3, gem-weighted rounds
	let cov = [0, 0], depl = 0;
	for (let r = 1; r <= final; r++) {
		const ps = bodies.map((b) => posAt(b, r)).filter(Boolean);
		let anyNear = false;
		for (const g of G) {
			const st = gstate(g.id, r);
			if (st !== 2) continue;
			const near = ps.some((p) => g.tiles.some((t) => cheb(t, p) <= 3));
			if (!near) cov[g.ours ? 0 : 1] += value(g.id);
			if (g.ours) anyNear = true;
		}
		if (!anyNear) depl++;
	}
	acc.cover[0] += cov[0] / final; acc.cover[1] += cov[1] / final;
	acc.depletedRounds += depl; acc.roundsAll += final;
	console.log(`${path.basename(file).padEnd(34)} r=${String(final).padStart(4)} ${d.meta.submitted[ourTeam]}-${d.meta.submitted[1 - ourTeam]} decisions=${gDec} skipped-nearer=${gSkip} ` +
		`lookahead-change=${gLaChange}/${gLa} idle-supply(gem-value per round) ours=${(cov[0] / final).toFixed(0)} theirs=${(cov[1] / final).toFixed(0)} no-untouched-group-on-our-half=${(100 * depl / final).toFixed(0)}%`);
}

const files = [];
for (const p of process.argv.slice(2)) {
	if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p).sort()) { if (f.endsWith('.repl26a')) files.push(path.join(p, f)); }
	else files.push(p);
}
for (const f of files) {
	try { await analyse(f); } catch (e) { console.log(f, 'FAILED', e.stack); }
}
const n = Math.max(1, acc.decisions);
console.log(`\n== ${acc.games} games, ${acc.decisions} target decisions, mean walk ${(acc.walk / n).toFixed(1)} steps`);
console.log(`capture targets (reward waiting): ${acc.captureDec} (${(100 * acc.captureDec / n).toFixed(1)}%); farm/wait target still respawning (wait on arrival): ${acc.respawnTarget} (${(100 * acc.respawnTarget / n).toFixed(1)}%)`);
console.log(`long walks (>20 steps): ${acc.longDec} decisions (${(100 * acc.longDec / n).toFixed(1)}%), ${acc.longWalk} steps (${(100 * acc.longWalk / Math.max(1, acc.walk)).toFixed(1)}% of target walking)`);
console.log(`nearer live group nobody targeted skipped by >5 steps: ${acc.skipped} (${(100 * acc.skipped / n).toFixed(1)}%), ${acc.skippedSteps} extra steps; of them long walks ${acc.skippedLong}`);
console.log(`no live untargeted group within 20 steps at decision: ${acc.noneNear} (${(100 * acc.noneNear / n).toFixed(1)}%)`);
console.log(`simple-model lookahead (gems/round of g1+g2 vs greedy g1): changes the first pick in ${acc.laChange} of ${acc.la} (${(100 * acc.laChange / Math.max(1, acc.la)).toFixed(1)}%), ` +
	`mean model gain when it changes ${(100 * acc.laGain / Math.max(1, acc.laChange)).toFixed(1)}%; mean g1->g2 walk greedy ${(acc.laD12 / Math.max(1, acc.la)).toFixed(1)} vs pair ${(acc.laD12best / Math.max(1, acc.la)).toFixed(1)}`);
console.log(`idle supply: live untouched groups with none of our bodies within 3, gem value per round (mean over games): ours ${(acc.cover[0] / acc.games).toFixed(0)} theirs ${(acc.cover[1] / acc.games).toFixed(0)}`);
console.log(`rounds with no untouched live group on our half: ${(100 * acc.depletedRounds / Math.max(1, acc.roundsAll)).toFixed(1)}%`);
