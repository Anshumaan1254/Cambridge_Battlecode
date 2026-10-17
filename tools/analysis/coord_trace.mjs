#!/usr/bin/env node
// Why did help not come? Joins coord_audit's death categories with the COORD_TRACE decision lines of our bot.
//
//   node tools/analysis/coord_trace.mjs DIR_OR_FILE...
//
// Replays must come from a COORD_TRACE build (bots/_x_coord with `#define COORD_TRACE 1`) run with a large
// --log-limit; NAME_A.repl26a = traced bot on team A (team-a.stdout), NAME_B = team B. Trace line per body turn
// when an enemy was seen within 12 in the last 2 rounds or a fresh alert is within 12:
//   CT r= i= ch= pos=x,y hp= gems= path= task= E= nd= adv= an= bk= fight= reach= alert= ad=
//   path: 1 fight, 2 flee/hold in combat(), 3 safety, 4 tribute, 5 home trip, 6 shop trip, 7 answer alert, 8 farm,
//         0 escort wait / channel. E = enemies combat() considered; an = allies within 6 counted; bk = backup.
//
// For every champion death of ours: the victim's last decision, and for each living ally within 10 that did not
// hit an enemy champion in r-3..r, its last decision in r-3..r (or "no line": no enemy within 12 and no alert).
import fs from 'node:fs';
import path from 'node:path';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';

process.removeAllListeners('warning');
const KIT = {
	Ryth: ['aoe_stun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'cc0'],
	Issac: ['reset', 'dash'], Stellar: ['dmg', 'aoe'], Prism: ['cc', 'aoe'], Marcella: ['reset', 'dmg'], Willow: ['heal', 'reset'],
	Ren: ['cc', 'dash'], Varg: ['reset', 'shield'], Tavi: ['reset', 'cc'],
};
const SELF_CAST = new Set(['dash', 'reset', 'shield', 'heal']);
const PATH = ['wait/chan', 'fight', 'flee', 'safety', 'tribute', 'home', 'shop', 'alert', 'farm'];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const H = {};
const inc = (k, n = 1) => { H[k] = (H[k] || 0) + n; };

function parseTrace(text) {
	const by = new Map(); // `${type}:${r}` -> line obj
	for (let line of text.split('\n')) {
		line = line.replace(/\x00/g, '').trim();
		if (!line.startsWith('CT ')) continue;
		const o = {};
		for (const kv of line.slice(3).split(' ')) { const [k, v] = kv.split('='); o[k] = v; }
		by.set(`${CHAMP[+o.ch]}:${o.r}`, o);
	}
	return by;
}

async function analyse(file) {
	const raw = fs.readFileSync(file);
	const ourTeam = /_B\.repl26a$/.test(file) ? 1 : 0;
	const tr = parseTrace(unwrapReplay(raw, ourTeam ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'));
	if (!tr.size) { console.error('no trace', file); return; }
	const d = await decode(unwrapReplay(raw), { every: 1 });
	const R = new Map(d.rounds.map((x) => [x.r, x]));
	const snap = (r) => R.get(r) || R.get(r - 1);
	const type = {}, team = {};
	for (const b of d.meta.bodies) { type[b.index] = b.type; team[b.index] = b.team; }
	const partner = (w) => {
		if (type[w] !== 'Cassi' && type[w] !== 'Issac') return -1;
		const p = d.meta.bodies.find((b) => b.team === team[w] && b.type === (type[w] === 'Cassi' ? 'Issac' : 'Cassi'));
		return p ? p.index : -1;
	};
	const hits = [], deaths = [];
	let curR = -1, live = {}, lastTo = null, lastRad = 0;
	for (const e of d.events) {
		if (e.r !== curR) {
			curR = e.r; live = {};
			const prev = snap(e.r - 1);
			if (prev) for (const c of prev.ch) live[c[0]] = { pos: [c[3], c[4]], alive: !!c[7] };
		}
		if (e.k === 'Death') {
			deaths.push({ r: e.r, who: e.who, at: e.at, bag: e.bag || 0, by: e.by, primary: lastTo ? cheb(e.at, lastTo) <= lastRad : true });
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
		if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) {
			const kind = e.k === 'Cast ability' ? KIT[type[w]]?.[e.slot] : 'atk';
			if (kind === 'dash' && live[w]) live[w].pos = e.to;
			if (!kind || SELF_CAST.has(kind)) continue;
			const rad = kind.startsWith('aoe') ? 1 : 0;
			for (const [v, c] of Object.entries(live))
				if (team[v] !== team[w] && c.alive && cheb(c.pos, e.to) <= rad) hits.push({ r: e.r, a: w, v: +v });
		}
	}
	for (const x of deaths) {
		const p = partner(x.who);
		const y = p >= 0 && deaths.find((z) => z.who === p && z.r === x.r);
		if (y && x.primary && y.primary) { if (deaths.indexOf(y) < deaths.indexOf(x)) x.primary = false; else y.primary = false; }
	}
	const hitsBy = (w, r0, r1) => hits.some((h) => h.a === w && h.r >= r0 && h.r <= r1);
	const lastLine = (w, r0, r1) => { for (let r = r1; r >= r0; r--) { const l = tr.get(`${type[w]}:${r}`); if (l) return l; } return null; };
	for (const x of deaths) {
		if (team[x.who] !== ourTeam || !x.primary || typeof x.by !== 'number' || team[x.by] === ourTeam) continue;
		inc('deaths');
		const p = partner(x.who);
		const mates = (snap(x.r - 1)?.ch || []).filter((c) => c[1] === ourTeam && c[7] && c[0] !== x.who && c[0] !== p);
		const near6 = mates.filter((c) => cheb([c[3], c[4]], x.at) <= 6);
		const near10 = mates.filter((c) => cheb([c[3], c[4]], x.at) <= 10);
		const joined = near10.some((c) => hitsBy(c[0], x.r - 3, x.r));
		const cat = !near6.length ? (near10.length ? (joined ? 'alone6-joined' : 'alone6-near10-nojoin') : 'alone10') : (joined ? 'near6-joined' : 'near6-nojoin');
		inc('cat ' + cat);
		// Victim's decisions in its last 3 turns.
		const vl = lastLine(x.who, x.r - 3, x.r - 1) || lastLine(x.who, x.r, x.r);
		if (vl) {
			inc(`victim path ${PATH[+vl.path]}`);
			inc(`victim ${cat} path ${PATH[+vl.path]}`);
			const adv = +vl.adv;
			inc(`victim adv ${adv < 0.5 ? '<0.5' : adv < 1 ? '0.5-1' : adv < 1.6 ? '1-1.6' : '>=1.6'}`);
			inc(`victim an=${vl.an} bk>0=${+vl.bk > 0 ? 1 : 0}`);
		} else inc('victim no line');
		if (near10.length && !joined) for (const c of near10) {
			inc('idle allies');
			const dd = cheb([c[3], c[4]], x.at);
			const l = lastLine(c[0], x.r - 3, x.r);
			if (!l) { inc(`idle no line d${dd <= 6 ? '<=6' : '7-10'}`); continue; }
			const reason = +l.path === 1 ? 'fight(other)' : +l.path === 2 ? (+l.reach ? 'flee(in reach)' : 'flee(isolated)') : PATH[+l.path];
			inc(`idle path ${reason}`);
			if (reason === 'farm') inc(`idle farm task=${l.task} hp${+l.hp >= 0.6 ? '>=.6' : '<.6'} alert=${l.alert} ad=${+l.ad <= 9 ? '<=9' : '>9'} E=${+l.E > 0 ? 1 : 0}`);
			inc(`idle E>0 ${+l.E > 0 ? 1 : 0} fight ${l.fight}`);
			if (+l.E > 0 && !+l.fight) {
				const adv = +l.adv;
				inc(`idle declined adv ${adv < 0.5 ? '<0.5' : adv < 1 ? '0.5-1' : adv < 1.3 ? '1-1.3' : '>=1.3'} an=${l.an}`);
			}
			inc(`idle hp ${+l.hp < 0.5 ? '<0.5' : +l.hp < 0.75 ? '0.5-0.75' : '>=0.75'}`);
			inc(`idle gems ${+l.gems >= 30 ? '30+' : +l.gems >= 10 ? '10-29' : '<10'}`);
			if (+l.alert) inc(`idle alert kind ${l.alert} ad ${+l.ad <= 9 ? '<=9' : '>9'}`);
		}
	}
}

const files = [];
for (const a of process.argv.slice(2)) {
	if (fs.statSync(a).isDirectory()) for (const f of fs.readdirSync(a)) { if (f.endsWith('.repl26a')) files.push(path.join(a, f)); }
	else files.push(a);
}
for (const f of files.sort()) {
	try { await analyse(f); } catch (e) { console.error('skip', f, e.message); }
}
for (const k of Object.keys(H).sort()) console.log(`${k.padEnd(48)} ${H[k]}`);
