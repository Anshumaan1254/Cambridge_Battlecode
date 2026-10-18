#!/usr/bin/env node
// Why our bodies die in fights (agent fight7, session 7). Needs an XM_TRACE + LEGEND_TRACE build as bench BOT_A
// (combat() prints FC/FX lines per evaluation, the turn end prints T lines with the task).
//
//   node tools/analysis/fight_deaths.mjs [--list] DIR...
//
// For every body death of ours: the dying body's FC lines over the 15 rounds before and its last task. Classes:
//   start     it chose a fight while it could still escape (fight=1 esc=1): visible enemies then (ne) vs enemies of
//             theirs within 9 of it the round before it died (replay), remembered hidden enemies at the start (FX mn)
//   fled      it walked away while in reach (fight=0 reach=1): esc at the first flee decision, walk home then
//   cornered  only esc=0 decisions
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';

const args = process.argv.slice(2);
const LIST = args.includes('--list');
const files = [];
for (const d of args.filter((a) => !a.startsWith('--'))) {
	const walk = (p) => {
		if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f));
		else if (p.endsWith('.repl26a')) files.push(p);
	};
	walk(d);
}
const TASK = ['none', 'farm', 'capt', 'wait', 'bank', 'home', 'fight', 'flee'];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const S = { deaths: 0, traced: 0, games: 0, task: {}, cls: {}, start_ne: {}, grow: {}, start_mn: {}, flee_esc: {}, flee_dh: {}, by_type: {}, start_by_type: {} };
const bump = (o, k, n = 1) => (o[k] = (o[k] || 0) + n);
for (const f of files.sort()) {
	const base = path.basename(f, '.repl26a');
	const side = base.slice(-1);
	const us = side === 'A' ? 0 : 1;
	const raw = fs.readFileSync(f);
	let text = '';
	try { text = unwrapReplay(raw, us ? 'team-b.stdout' : 'team-a.stdout').toString('latin1').replace(/\x00/g, ''); } catch { continue; }
	const fc = {}, fx = {}, tl = {};
	for (const l of text.split('\n')) {
		const t = l.trim();
		if (t.startsWith('FC ') || t.startsWith('FX ')) {
			const kv = Object.fromEntries(t.slice(3).split(' ').map((s) => s.split('=')));
			((t[1] === 'C' ? fc : fx)[kv.ty] ||= new Map()).set(+kv.r, kv);
		} else if (t.startsWith('T r=')) {
			const m = t.match(/^T r=(\d+) (\d+) task=(\d+)/);
			if (m) (tl[m[2]] ||= new Map()).set(+m[1], +m[3]);
		}
	}
	const d = await decode(unwrapReplay(raw));
	S.games++;
	const typeOf = {};
	for (const b of d.meta.bodies) typeOf[b.index] = CHAMP.indexOf(b.type);
	const byR = new Map(d.rounds.map((r) => [r.r, r]));
	for (const e of d.events) {
		if (e.k !== 'Death' || e.team !== us) continue;
		S.deaths++;
		const ty = String(typeOf[e.who]);
		bump(S.by_type, CHAMP[+ty]);
		let task = 'unknown';
		const T = tl[ty];
		if (T) for (let r = e.r - 1; r >= e.r - 3; --r) if (T.has(r)) { task = TASK[T.get(r)]; break; }
		bump(S.task, task);
		const L = [];
		const F = fc[ty] || new Map();
		for (let r = e.r - 15; r < e.r; ++r) if (F.has(r)) L.push(F.get(r));
		if (!L.length) { bump(S.cls, 'no-fc'); continue; }
		S.traced++;
		const prev = byR.get(e.r - 1) || byR.get(e.r);
		const me = prev.ch.find((c) => c[0] === e.who);
		const near = me ? prev.ch.filter((c) => c[1] !== us && c[7] && cheb([c[3], c[4]], [me[3], me[4]]) <= 9).length : 0;
		const start = L.find((x) => x.fight === '1' && x.esc === '1');
		const flee = L.find((x) => x.fight === '0' && x.reach === '1');
		let cls;
		if (start) {
			cls = 'start';
			bump(S.start_ne, start.ne);
			bump(S.grow, `${start.ne}->${near}`);
			const X = (fx[ty] || new Map()).get(+start.r);
			bump(S.start_mn, X ? X.mn : '?');
			bump(S.start_by_type, CHAMP[+ty]);
			cls += +start.adv >= +start.fm ? '-margin' : start.kill === '1' ? '-kill' : start.reach === '1' ? '-back' : '-other';
		} else if (flee) {
			cls = 'fled';
			bump(S.flee_esc, flee.esc);
		} else if (L.some((x) => x.esc === '0')) cls = 'cornered';
		else cls = 'other';
		bump(S.cls, cls);
		if (LIST) {
			console.log(`${base} r${e.r} ${CHAMP[+ty]} task ${task} cls ${cls} near ${near} bag ${e.bag}`);
			for (const x of L) console.log(`   r${x.r} hp ${(+x.hp).toFixed(0)}/${x.mhp} adv ${(+x.adv).toFixed(2)} fight ${x.fight} kill ${x.kill} reach ${x.reach} esc ${x.esc} iso ${x.iso} ne ${x.ne} na ${x.na} inc ${x.inc} tdie ${x.tdie} pos ${x.x},${x.y}`);
		}
	}
}
console.log(`games ${S.games}, deaths ${S.deaths} (${(S.deaths / Math.max(1, S.games)).toFixed(2)}/game), with FC lines ${S.traced}`);
console.log('by type', JSON.stringify(S.by_type));
console.log('last task', JSON.stringify(S.task));
console.log('class', JSON.stringify(S.cls));
console.log('start: visible enemies at the start', JSON.stringify(S.start_ne));
console.log('start: remembered hidden enemies at the start (mn)', JSON.stringify(S.start_mn));
console.log('start: visible at start -> enemies within 9 at death', JSON.stringify(S.grow));
console.log('start by type', JSON.stringify(S.start_by_type));
console.log('fled: esc at the first flee decision', JSON.stringify(S.flee_esc));
