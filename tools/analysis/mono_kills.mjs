#!/usr/bin/env node
// Monolith kills per map: who kills the monoliths, when, with how many bodies (basic hits in the 60 rounds before the kill).
//
//   node tools/analysis/mono_kills.mjs [--json OUT] FILE_OR_DIR...
//
// Map name = the file name up to its last "_" (<map>_<A|B> from tools/ledger.py --keep, <map>_<id> from the ladder archive).
// Per map: games, monoliths, kills a game, the first kill's round (median), hitters per kill, and the kills by the side named in the file
// (A / B for --keep files: "us" = the side in the name) when the file name ends in _A or _B.
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const median = (xs) => { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b); return s[(s.length - 1) >> 1]; };

async function analyse(file, perMap) {
	const base = path.basename(file).replace(/\.repl26a$/, '');
	const map = base.replace(/_[^_]+$/, '');
	const side = /_([AB])$/.exec(base);
	const ours = side ? (side[1] === 'B' ? 1 : 0) : -1;
	const d = await decode(unwrapReplay(fs.readFileSync(file)), { every: 1 });
	const mono = [];
	d.meta.camps.forEach((c, k) => { if (c.type === 'monolith') mono.push(k); });
	const M = (perMap[map] ||= { games: 0, monos: 0, kills: 0, oursKills: 0, theirsKills: 0, first: [], hitters: [], rounds: [] });
	M.games++;
	M.monos = mono.length;
	if (!mono.length) return;
	const byRound = new Map(d.rounds.map((r) => [r.r, r]));
	let first = null;
	for (const k of mono) {
		const pos = [d.meta.camps[k].x, d.meta.camps[k].y];
		for (let r = 2; r <= d.meta.finalRound; r++) {
			const a = byRound.get(r - 1), b = byRound.get(r);
			if (!a || !b || !(a.campHp[k] > 0) || b.campHp[k] > 0) continue;
			// The team that hit it most in the last 60 rounds killed it.
			const hits = [new Set(), new Set()], n = [0, 0];
			for (const e of d.events) {
				if (e.k !== 'Attack' || !e.to || e.r < r - 60 || e.r > r || e.to[0] !== pos[0] || e.to[1] !== pos[1] || e.team === undefined) continue;
				hits[e.team].add(e.who);
				n[e.team]++;
			}
			const t = n[1] > n[0] ? 1 : 0;
			M.kills++;
			M.hitters.push(hits[t].size);
			M.rounds.push(r);
			if (ours >= 0) { if (t === ours) M.oursKills++; else M.theirsKills++; }
			if (first === null || r < first) first = r;
		}
	}
	if (first !== null) M.first.push(first);
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('mono_kills.mjs')) {
	const argv = process.argv.slice(2);
	let json = null;
	const files = [];
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--json') { json = argv[++i]; continue; }
		const a = argv[i];
		if (fs.statSync(a).isDirectory()) { for (const f of fs.readdirSync(a).sort()) if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
		else files.push(a);
	}
	const perMap = {};
	for (const f of files) {
		try { await analyse(f, perMap); } catch (e) { console.log(f, 'FAILED', e.message); }
	}
	let g = 0, k = 0, ko = 0, kt = 0;
	console.log('map'.padEnd(26) + 'games monos kills/game first-kill(med) hitters(med) ours/theirs');
	for (const [m, v] of Object.entries(perMap).sort()) {
		if (!v.monos) continue;
		g += v.games, k += v.kills, ko += v.oursKills, kt += v.theirsKills;
		console.log(`${m.padEnd(26)}${String(v.games).padStart(5)}${String(v.monos).padStart(6)}${(v.kills / v.games).toFixed(2).padStart(11)}${String(median(v.first) ?? '-').padStart(17)}${String(median(v.hitters) ?? '-').padStart(13)}   ${v.oursKills}/${v.theirsKills}`);
	}
	console.log(`total: ${g} games on monolith maps, ${(k / Math.max(1, g)).toFixed(2)} kills a game, ours ${ko} theirs ${kt}`);
	if (json) fs.writeFileSync(json, JSON.stringify(perMap));
}
