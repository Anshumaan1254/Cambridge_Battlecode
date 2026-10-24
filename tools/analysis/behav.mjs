#!/usr/bin/env node
// Behaviour counts the user asked about (Oct 24: "stuttering, moving away from the altar with good gems, monoliths not killed, wards
// thrown at random tiles"), per team, from local or ladder replays:
//
//   node tools/analysis/behav.mjs [--team us|opp|both] [--per-map] FILE_OR_DIR...
//
// Files named <map>_<A|B>.repl26a (tools/ledger.py --keep): "us" = the side in the name, "opp" = the other one.
//   bag      body-rounds alive off spawn carrying >= 40 / >= 80 gems; of those: walking away from the nearest altar (the walk distance to
//            a tile next to an altar grew) with no enemy within 5, standing still doing nothing (no move, attack, cast, channel, capture)
//            with no enemy within 5; bags lost at death (gems the dead body carried) and how many deaths carried >= 40
//   bank     tribute events, gems banked, mean bag at the tribute, gem-rounds carried per gem banked (how long gems ride in the field)
//   mono     monolith camps on the map, kills (hp > 0 -> 0) by the team that captured the reward afterwards, monolith gems captured,
//            basic attacks into monolith tiles
//   ward     wards placed, the share placed on a bush tile, the share placed while a bush tile was within 2 (placement reach) of the body,
//            and how many of those went to a non-bush tile
//   osc      short oscillations: windows of 10 rounds, alive, off spawn, no enemy within 5, no attack / cast / channel / capture, at least 6
//            moves, ending within 1 tile of where they started (A-B-A walking; tools/analysis/stuck.mjs has the long-episode detector)
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';
import { mapGrid } from './stuck.mjs';

process.removeAllListeners('warning');
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

function bfs(w, h, blocked, roots) {
	const d = new Int32Array(w * h).fill(1 << 20);
	const q = new Int32Array(w * h);
	let qh = 0, qt = 0;
	for (const i of roots) if (d[i] !== 0) { d[i] = 0; q[qt++] = i; }
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

function newAcc() {
	return {
		games: 0, wins: 0, gemsFor: 0, gemsAgainst: 0, alive: 0,
		bag40: 0, bag80: 0, away40: 0, away80: 0, idle40: 0, idle80: 0, deaths: 0, deathBag: 0, deaths40: 0,
		banks: 0, banked: 0, gemRounds: 0,
		monoMaps: 0, monoKills: 0, monoKillsOpp: 0, monoGems: 0, monoHits: 0,
		wards: 0, wardBush: 0, wardBushInReach: 0, wardMissedBush: 0,
		osc: 0, oscRounds: 0,
	};
}

async function analyse(file, accs, opts, perMap) {
	const raw = fs.readFileSync(file);
	const base = path.basename(file).replace(/\.repl26a$/, '');
	const mapName = base.replace(/_[AB]$/, '');
	const ours = /_B$/.test(base) ? 1 : 0;
	const rep = unwrapReplay(raw);
	const d = await decode(rep, { every: 1 });
	const grid = await mapGrid(rep);
	const { w, h } = grid;
	const byRound = new Map(d.rounds.map((r) => [r.r, r]));
	const final = d.meta.finalRound;
	// Per round and body: actions.
	const ev = new Map();
	const get = (r, who) => { const k = r + ':' + who; let o = ev.get(k); if (!o) ev.set(k, (o = {})); return o; };
	for (const e of d.events) {
		if (e.who === undefined) continue;
		const o = get(e.r, e.who);
		if (e.k === 'Move') o.move = true;
		else if (e.k === 'Attack') { o.act = true; o.hit = e.to; }
		else if (e.k === 'Cast ability') { if (e.ability === 6) o.move = true; else o.act = true; }
		else if (e.k === 'Recall' || e.k === 'Submit gems' || e.k === 'Teleport channel') o.chan = true;
		else if (e.k === 'Place ward') o.ward = e.to;
	}
	// Static fields: walk distance to a tile next to an altar, per team (the enemy spawn blocks).
	const altarRoots = [];
	for (let i = 0; i < w * h; i++) if (grid.altar[i]) {
		const x = i % w, y = (i / w) | 0;
		for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
			const nx = x + dx, ny = y + dy;
			if ((dx || dy) && nx >= 0 && ny >= 0 && nx < w && ny < h) altarRoots.push(ny * w + nx);
		}
	}
	const altarField = [0, 1].map((t) => {
		const blocked = new Uint8Array(w * h);
		for (let i = 0; i < w * h; i++) blocked[i] = grid.wall[i] | grid.hole[i] | grid.altar[i] | grid.spawn[1 - t][i];
		return bfs(w, h, blocked, altarRoots.filter((i) => !blocked[i]));
	});
	const tileGroup = new Map();
	for (const g of grid.groups) for (const t of g.tiles) tileGroup.set(t[0] + ',' + t[1], g.id);
	const monoIdx = [];
	d.meta.camps.forEach((c, k) => { if (c.type === 'monolith') monoIdx.push(k); });
	const monoTile = new Set(monoIdx.map((k) => d.meta.camps[k].x + ',' + d.meta.camps[k].y));
	const teams = opts.team === 'both' ? [ours, 1 - ours] : opts.team === 'opp' ? [1 - ours] : [ours];
	for (const team of teams) {
		const key = opts.team === 'both' ? (team === ours ? 'us' : 'opp') : opts.team;
		const A = accs[key];
		const M = perMap ? (perMap[key + ' ' + mapName] ||= newAcc()) : null;
		const add = (k, v = 1) => { A[k] += v; if (M) M[k] += v; };
		add('games');
		if (d.meta.outcome === team + 1) add('wins');
		add('gemsFor', d.meta.submitted[team]);
		add('gemsAgainst', d.meta.submitted[1 - team]);
		const bodies = d.meta.bodies.filter((b) => b.team === team).map((b) => b.index);
		const enemies = d.meta.bodies.filter((b) => b.team !== team).map((b) => b.index);
		for (const b of bodies) {
			let prev = null;
			let lastChan = -99;
			const hist = []; // per round: {pos, elig, moved}
			for (let r = 1; r <= final; r++) {
				const s = byRound.get(r);
				if (!s) continue;
				const c = s.ch.find((q) => q[0] === b);
				if (!c) continue;
				const alive = c[7] === 1, pos = [c[3], c[4]], gems = c[8];
				const o = ev.get(r + ':' + b) || {};
				if (o.chan) lastChan = r;
				if (o.ward && alive) {
					add('wards');
					const wi = o.ward[1] * w + o.ward[0];
					const onBush = grid.bush[wi] === 1;
					if (onBush) add('wardBush');
					let inReach = false;
					const p0 = prev && prev.alive ? prev.pos : pos;
					for (let dy = -2; dy <= 2 && !inReach; dy++) for (let dx = -2; dx <= 2; dx++) {
						const x = p0[0] + dx, y = p0[1] + dy;
						if (x >= 0 && y >= 0 && x < w && y < h && grid.bush[y * w + x]) { inReach = true; break; }
					}
					if (inReach) { add('wardBushInReach'); if (!onBush) add('wardMissedBush'); }
				}
				const onSpawn = alive && grid.spawn[team][pos[1] * w + pos[0]] === 1;
				let near = false;
				if (alive) for (const k of enemies) {
					const e = s.ch.find((q) => q[0] === k);
					if (e && e[7] && cheb([e[3], e[4]], pos) <= 5) { near = true; break; }
				}
				const gid = tileGroup.get(pos[0] + ',' + pos[1]);
				const prevS = byRound.get(r - 1);
				const capturing = alive && gid !== undefined && (s.gr[gid] || (prevS && prevS.gr[gid]));
				const moved = alive && prev && prev.alive && (pos[0] !== prev.pos[0] || pos[1] !== prev.pos[1]);
				if (alive) add('alive');
				if (alive && !onSpawn) add('gemRounds', gems);
				if (alive && !onSpawn && gems >= 40) {
					add('bag40');
					if (gems >= 80) add('bag80');
					const df = altarField[team];
					const dNow = df[pos[1] * w + pos[0]];
					const dPrev = prev && prev.alive ? df[prev.pos[1] * w + prev.pos[0]] : dNow;
					if (!near && moved && dNow > dPrev && dNow < 1 << 20) { add('away40'); if (gems >= 80) add('away80'); }
					const busy = o.act || o.chan || r - lastChan <= 5 || capturing || dNow === 0;
					if (!near && !moved && !busy) { add('idle40'); if (gems >= 80) add('idle80'); }
				}
				if (prev && prev.alive && !alive) {
					add('deaths');
					add('deathBag', prev.gems);
					if (prev.gems >= 40) add('deaths40');
				}
				// Short oscillation windows.
				const elig = alive && !onSpawn && !near && !o.act && !o.chan && r - lastChan > 5 && !capturing;
				hist.push({ pos, elig, moved });
				prev = { alive, pos, gems };
			}
			let i = 0;
			while (i + 10 <= hist.length) {
				const win = hist.slice(i, i + 10);
				if (win.every((x) => x.elig) && win.filter((x) => x.moved).length >= 6 && cheb(win[0].pos, win[9].pos) <= 1) {
					// Extend while the body keeps returning.
					let j = i + 10;
					while (j < hist.length && hist[j].elig && cheb(hist[j].pos, win[0].pos) <= 2) j++;
					add('osc');
					add('oscRounds', j - i);
					i = j;
				} else i++;
			}
		}
		for (const e of d.events) {
			if (e.team !== team) continue;
			if (e.k === 'Banked') { add('banks'); add('banked', e.gems); }
			if (e.k === 'Attack' && e.to && monoTile.has(e.to[0] + ',' + e.to[1])) add('monoHits');
			if (e.k === 'CaptureGems' && e.at && monoIdx.length) {
				const gid = tileGroup.get(e.at[0] + ',' + e.at[1]);
				if (gid !== undefined && grid.groups[gid].tiles.some((t) => monoTile.has(t[0] + ',' + t[1]))) add('monoGems', e.gems);
			}
		}
		if (monoIdx.length) {
			add('monoMaps');
			// A monolith kill belongs to the team whose body captured that group's reward next.
			for (const k of monoIdx) {
				const cx = d.meta.camps[k].x, cy = d.meta.camps[k].y, gid = tileGroup.get(cx + ',' + cy);
				for (let r = 2; r <= final; r++) {
					const a = byRound.get(r - 1), bb = byRound.get(r);
					if (!a || !bb || !(a.campHp[k] > 0) || bb.campHp[k] > 0) continue;
					const cap = d.events.find((e) => e.k === 'CaptureGems' && e.r >= r && e.r <= r + 60 && e.at && tileGroup.get(e.at[0] + ',' + e.at[1]) === gid);
					if (cap && cap.team === team) add('monoKills');
					else if (cap) add('monoKillsOpp');
				}
			}
		}
	}
}

function fmt(A, label) {
	const pct = (a, b) => (b ? (100 * a / b).toFixed(1) + '%' : '-');
	const g = Math.max(1, A.games);
	return [
		`== ${label}: ${A.games} games, won ${A.wins}, gems ${(A.gemsFor / g).toFixed(0)}-${(A.gemsAgainst / g).toFixed(0)} a game`,
		`  bag >= 40: ${(A.bag40 / g).toFixed(0)} body-rounds a game, away from the altar ${pct(A.away40, A.bag40)}, idle ${pct(A.idle40, A.bag40)};` +
			` >= 80: ${(A.bag80 / g).toFixed(0)}, away ${pct(A.away80, A.bag80)}, idle ${pct(A.idle80, A.bag80)}`,
		`  deaths ${(A.deaths / g).toFixed(1)} a game, gems lost at death ${(A.deathBag / g).toFixed(0)} a game, deaths carrying >= 40 ${(A.deaths40 / g).toFixed(1)}`,
		`  banks ${(A.banks / g).toFixed(1)} a game, ${(A.banked / g).toFixed(0)} gems, mean bag ${(A.banked / Math.max(1, A.banks)).toFixed(1)}, gem-rounds per gem banked ${(A.gemRounds / Math.max(1, A.banked)).toFixed(1)}`,
		`  monolith maps ${A.monoMaps}: kills ${A.monoKills} (theirs ${A.monoKillsOpp}), monolith gems ${A.monoGems}, basic hits on monoliths ${A.monoHits}`,
		`  wards ${(A.wards / g).toFixed(1)} a game, on a bush ${pct(A.wardBush, A.wards)}, bush within reach ${pct(A.wardBushInReach, A.wards)}, of those placed off the bush ${pct(A.wardMissedBush, A.wardBushInReach)}`,
		`  oscillation windows ${(A.osc / g).toFixed(1)} a game, ${(A.oscRounds / g).toFixed(1)} body-rounds a game (${(1000 * A.oscRounds / Math.max(1, A.alive)).toFixed(2)} per 1000 alive)`,
	].join('\n');
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('behav.mjs')) {
	const argv = process.argv.slice(2);
	const opts = { team: 'us', perMap: false, json: null };
	const files = [];
	for (let i = 0; i < argv.length; i++) {
		const a = argv[i];
		if (a === '--team') { opts.team = argv[++i]; continue; }
		if (a === '--per-map') { opts.perMap = true; continue; }
		if (a === '--json') { opts.json = argv[++i]; continue; }
		if (fs.statSync(a).isDirectory()) { for (const f of fs.readdirSync(a).sort()) if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
		else files.push(a);
	}
	const accs = { us: newAcc(), opp: newAcc() };
	const perMap = opts.perMap ? {} : null;
	for (const f of files) {
		try { await analyse(f, accs, opts, perMap); } catch (e) { console.log(f, 'FAILED', e.message); }
	}
	for (const k of opts.team === 'both' ? ['us', 'opp'] : [opts.team]) console.log(fmt(accs[k], k));
	if (perMap) for (const [k, v] of Object.entries(perMap).sort()) console.log(fmt(v, k));
	if (opts.json) fs.writeFileSync(opts.json, JSON.stringify({ accs, perMap }));
}
