// usage: node tools/analysis/spell_usage.mjs DIR [DIR...]  -> ability usage per side (us = bench BOT_A) x champion x slot.
// Ready = 8+ rounds since the slot's last cast (min gap measured = 8), alive, own turn, not channelling,
// not stunned, no fuel rollover. "Wasted" = ready, no cast at all this turn (one cast per turn), and a
// target in range 4 at the start of the turn.
import fs from 'fs'; import path from 'path';
import { decode, unwrapReplay } from './spell_decode.mjs';

const KIT = {
	Ryth: ['aoe_stun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'cc0'],
	Issac: ['reset', 'dash'], Stellar: ['dmg', 'aoe'], Prism: ['cc', 'aoe'], Marcella: ['reset', 'dmg'], Willow: ['heal', 'reset'],
	Ren: ['cc', 'dash'], Varg: ['reset', 'shield'], Tavi: ['reset', 'cc'],
};
const STUN = new Set(['aoe_stun', 'cc0', 'cc']);
const RANGED_SPELL = new Set(['aoe_stun', 'cc0', 'cc', 'dmg', 'aoe']);
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

const dirs = process.argv.slice(2);
const files = dirs.flatMap(p => fs.statSync(p).isDirectory() ? fs.readdirSync(p).filter(f => f.endsWith('.repl26a')).map(f => path.join(p, f)) : [p]);
const S = {}; // key side|champ|slot
const G = { us: {}, them: {} }; // misc per side
const key = (side, champ, slot) => `${side}|${champ}|${slot}:${KIT[champ][slot]}`;
const st = (k) => S[k] ??= { turns: 0, ready: 0, casts: 0, onChamp: 0, onCamp: 0, other: 0, wasteChamp: 0, wasteCampSafe: 0, wasteCampNear: 0, readyNoTarget: 0,
	atkTurns: 0, missedReset: 0, properReset: 0, resetNoFollow: 0, resetBeforeAtk: 0, dashCombat: 0,
	stunBefore: 0, stunAfter: 0, stunFocus: 0, stunKill: 0, stunChannel: 0,
	shieldHitWin: 0, shieldHitsIn: 0, shieldIdle: 0, readyHit: 0 };
const gi = (side, k, v = 1) => { G[side][k] = (G[side][k] || 0) + v; };

for (const f of files) {
	const ourTeam = f.endsWith('_A.repl26a') ? 0 : 1;
	let d;
	try { d = await decode(unwrapReplay(fs.readFileSync(f)), { every: 1, rollovers: true, endturns: true }); } catch (e) { console.error('skip', f, e.message); continue; }
	const R = new Map(d.rounds.map(x => [x.r, x]));
	const bodies = d.meta.bodies; const type = {}; const team = {};
	for (const b of bodies) { type[b.index] = b.type; team[b.index] = b.team; }
	const camps = d.meta.camps;
	const sideOf = (who) => team[who] === ourTeam ? 'us' : 'them';
	for (const s of ['us', 'them']) gi(s, 'games');
	const lastCast = {}; // who -> [r0, r1]
	const chanUntil = {}; const stunLost = {}; const rolled = {};
	let curR = -1; let live = {}; let ended = new Set(); let turnEv = {};
	const hitsOn = {}; // who -> rounds hit by an enemy champion (attack/cast landing on its tile)
	const campHitsOn = {}; // who -> rounds hit by a camp
	const exch = {}; // who -> Set of rounds it hit or was hit by an enemy champion
	const held = []; // [who, r, key] ready damage/stun spell not cast with a camp in range and an enemy within 9
	const fightIdle = []; // [who, r, key] ready spell not cast while an enemy champion was within 4
	// pre-pass: hits per champion per round (attack/cast 'to' equal to the champion's live position)
	const evs = d.events;
	const startState = (r) => {
		const prev = R.get(r - 1) || R.get(r);
		live = {};
		for (const c of prev.ch) live[c[0]] = { pos: [c[3], c[4]], alive: !!c[7], hp: c[5], max: c[6], gems: c[8] };
		ended = new Set(); turnEv = {};
	};
	const enemyAt = (casterTeam, tile, rad) => Object.entries(live).filter(([w, c]) => team[w] !== casterTeam && c.alive && cheb(c.pos, tile) <= rad).map(([w]) => +w);
	const campAt = (r, tile, rad) => { const hp = (R.get(r - 1) || R.get(r)).campHp; return camps.some((c, i) => hp[i] > 0 && cheb([c.x, c.y], tile) <= rad); };
	const stunEvents = []; // {r, idx, caster, targets, lostRound}
	for (let i = 0; i < evs.length; i++) {
		const e = evs[i];
		if (e.r !== curR) { curR = e.r; startState(curR); }
		if (e.camp !== undefined && e.k === 'Attack' && e.to) {
			for (const [tw, c] of Object.entries(live)) if (c.alive && c.pos[0] === e.to[0] && c.pos[1] === e.to[1]) (campHitsOn[tw] ??= []).push(e.r);
		}
		if (e.who === undefined) continue;
		const w = e.who;
		(turnEv[w] ??= []).push([i, e]);
		if (e.k === 'Move' && live[w]) live[w].pos = e.to;
		if (e.k === 'Death' && live[w]) live[w].alive = false;
		if (e.k === 'Recall') chanUntil[w] = e.r + 4;
		if (e.k === 'Submit gems') chanUntil[w] = e.r + Math.max(1, Math.ceil((live[w]?.gems || 0) / 10)) - 1;
		if (e.k === 'Teleport channel') chanUntil[w] = e.r + 2;
		if (e.k === 'Cancel channel') chanUntil[w] = e.r;
		if (e.k === 'Turn rollover') { rolled[`${w}:${e.r}`] = 1; rolled[`${w}:${e.r + 1}`] = 1; }
		if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to) {
			for (const [tw, c] of Object.entries(live)) if (team[tw] !== team[w] && c.alive && cheb(c.pos, e.to) <= (e.k === 'Cast ability' && KIT[type[w]][e.slot]?.startsWith('aoe') ? 1 : 0)) {
				(hitsOn[tw] ??= []).push(e.r); (exch[tw] ??= new Set()).add(e.r); (exch[w] ??= new Set()).add(e.r);
			}
		}
		if (e.k === 'Cast ability') {
			const kind = KIT[type[w]][e.slot];
			if (kind === 'dash' && e.to && live[w]) live[w].pos = e.to;
			if (STUN.has(kind) && e.to) {
				const tg = enemyAt(team[w], e.to, kind === 'aoe_stun' ? 1 : 0);
				for (const t of tg) {
					const after = ended.has(t);
					const lost = after ? e.r + 1 : e.r;
					stunLost[`${t}:${lost}`] = 1;
					stunEvents.push({ r: e.r, idx: i, caster: w, target: t, lost, after, chan: (chanUntil[t] ?? -1) >= e.r });
				}
			}
		}
		if (e.k === 'End turn') {
			ended.add(w);
			// evaluate this turn
			const acts = turnEv[w].map(x => x[1]);
			const r = e.r; const side = sideOf(w); const champ = type[w];
			const prev = R.get(r - 1) || R.get(r), cur = R.get(r) || prev;
			const pc = prev.ch.find(c => c[0] === w), cc = cur.ch.find(c => c[0] === w);
			const aliveTurn = (pc && pc[7] && !(acts.some(a => a.k === 'Death') && !acts.some(a => a.k !== 'Death' && a.k !== 'End turn'))) || (!pc?.[7] && cc?.[7]);
			if (!aliveTurn) { turnEv[w] = []; continue; }
			gi(side, 'aliveTurns');
			const channel = (chanUntil[w] ?? -1) >= r && !acts.some(a => a.k === 'Recall' || a.k === 'Submit gems' || a.k === 'Teleport channel');
			const stunned = !!stunLost[`${w}:${r}`];
			const roll = !!rolled[`${w}:${r}`];
			if (channel) gi(side, 'chanTurns');
			if (stunned) gi(side, 'stunnedTurns');
			if (roll) gi(side, 'rollTurns');
			const startPos = (acts.find(a => a.k === 'Move' || (a.k === 'Cast ability' && KIT[champ][a.slot] === 'dash'))?.from) || live[w].pos;
			const casts = acts.filter(a => a.k === 'Cast ability');
			const attacks = acts.filter(a => a.k === 'Attack');
			let enemyIn4 = false, enemyIn6 = false, enemyIn9 = false, minD = 99, chanIn4 = false;
			for (const [tw, c] of Object.entries(live)) if (team[tw] !== team[w] && c.alive) {
				const dd = cheb(c.pos, startPos);
				minD = Math.min(minD, dd);
				if (dd <= 4 && (chanUntil[tw] ?? -1) >= r) chanIn4 = true;
				if (dd <= 4) enemyIn4 = true; if (dd <= 6) enemyIn6 = true; if (dd <= 9) enemyIn9 = true;
			}
			const campIn4 = campAt(r, startPos, 4);
			if (enemyIn9) gi(side, 'turnsEnemy9');
			for (const slot of [0, 1]) {
				const kind = KIT[champ][slot];
				const s = st(key(side, champ, slot));
				const lc = lastCast[w]?.[slot] ?? -100;
				const usable = !channel && !stunned && !roll;
				s.turns += usable ? 1 : 0;
				const ready = usable && r - lc >= 8;
				const myCasts = casts.filter(c => c.slot === slot);
				if (ready) s.ready++;
				for (const c of myCasts) {
					s.casts++;
					if (c.to && RANGED_SPELL.has(kind)) {
						const rad = kind.startsWith('aoe') ? 1 : 0;
						if (enemyAt(team[w], c.to, rad).length) s.onChamp++; else if (campAt(r, c.to, rad)) s.onCamp++; else s.other++;
					}
					if (kind === 'dash' && enemyIn6) s.dashCombat++;
					if (kind === 'reset') {
						const ci = acts.indexOf(c);
						const before = acts.slice(0, ci).some(a => a.k === 'Attack'), afterA = acts.slice(ci + 1).some(a => a.k === 'Attack');
						if (before && afterA) s.properReset++; else if (!before && afterA) s.resetBeforeAtk++; else s.resetNoFollow++;
					}
					if (kind === 'shield') {
						const hits = (hitsOn[w] || []).filter(x => x >= r && x <= r + 4).length; // updated later in a second pass
						s._shieldCasts = (s._shieldCasts || []); s._shieldCasts.push([w, r]);
					}
				}
				if (myCasts.length) { (lastCast[w] ??= [-100, -100])[slot] = r; }
				if (!ready) continue;
				const anyCast = casts.length > 0;
				if (chanIn4 && RANGED_SPELL.has(kind)) { gi(side, 'chanOpp_' + kind); if (casts.some(c => c.slot === slot)) gi(side, 'chanHit_' + kind); }
				if (kind === 'reset') {
					if (attacks.length) { s.atkTurns++; if (!anyCast) s.missedReset++; }
					continue;
				}
				if (kind === 'shield') { if (!anyCast) { s._idle = s._idle || []; s._idle.push([w, r]); } continue; }
				if (!RANGED_SPELL.has(kind)) continue;
				if (anyCast) continue;
				const act = attacks.length ? 'atk' : (acts.some(a => a.k === 'Move') ? 'move' : 'idle');
				if (enemyIn4) { s.wasteChamp++; s['wc_' + act] = (s['wc_' + act] || 0) + 1; fightIdle.push([w, r, key(side, champ, slot)]); }
				else if (campIn4 && !enemyIn9) { s.wasteCampSafe++; s['ws_' + act] = (s['ws_' + act] || 0) + 1; }
				else if (campIn4) { s.wasteCampNear++; held.push([w, r, key(side, champ, slot), minD, side, act]); }
				else s.readyNoTarget++;
			}
			turnEv[w] = [];
		}
		if (e.k === 'Place ward') gi(sideOf(w), 'wards');
		if (e.k === 'Place altar lock') gi(sideOf(w), 'locks');
		if (e.k === 'Consumable') gi(sideOf(w), 'consumable');
		if (e.k === 'Teleport channel') gi(sideOf(w), 'tpChannel');
		if (e.k === 'Teleport complete') gi(sideOf(w), 'tpDone');
		if (e.k === 'Death') { gi(sideOf(w), 'deaths'); gi(sideOf(w), 'bagLost', e.bag || 0); }
	}
	// shield windows and stun follow-ups need the whole game
	for (const s of Object.values(S)) {
		for (const [w, r] of s._shieldCasts || []) { const h = [...(hitsOn[w] || []), ...(campHitsOn[w] || [])].filter(x => x >= r && x <= r + 5).length; s.shieldHitsIn += h; if (h > 0) s.shieldHitWin++; }
		for (const [w, r] of s._idle || []) { if ([...(hitsOn[w] || []), ...(campHitsOn[w] || [])].some(x => x === r + 1)) s.readyHit++; s.shieldIdle++; }
		delete s._shieldCasts; delete s._idle;
	}
	for (const [w, r, k, minD, side, act] of held) {
		const s = S[k]; s.heldN = (s.heldN || 0) + 1;
		const ex = exch[w] || new Set();
		let f = false, f4 = false; for (let x = r + 1; x <= r + 8; x++) if (ex.has(x)) { f = true; if (x <= r + 3) f4 = true; break; }
		if (f) s.heldFight = (s.heldFight || 0) + 1;
		const b = minD <= 6 ? 'd5-6' : 'd7-9';
		gi(side, 'held_' + b); if (f) gi(side, 'heldF_' + b); if (f4) gi(side, 'heldF3_' + b);
		gi(side, 'heldAct_' + act + '_' + b); if (f) gi(side, 'heldActF_' + act + '_' + b);
	}
	for (const [w, r, k] of fightIdle) {
		const s = S[k]; const ex = exch[w] || new Set();
		if (ex.has(r) || ex.has(r + 1)) s.fightIdleEx = (s.fightIdleEx || 0) + 1;
	}
	for (const se of stunEvents) {
		const s = st(key(sideOf(se.caster), type[se.caster], KIT[type[se.caster]].indexOf(KIT[type[se.caster]].find(k => STUN.has(k)))));
		if (se.after) s.stunAfter++; else s.stunBefore++;
		if (se.chan) s.stunChannel++;
		// allies (incl. caster) hitting the target before it can act again
		let focus = 0;
		for (let j = se.idx + 1; j < evs.length && evs[j].r <= se.lost; j++) {
			const x = evs[j];
			if ((x.k === 'Attack' || x.k === 'Cast ability') && x.who !== undefined && team[x.who] === team[se.caster] && x.to) {
				const tc = (R.get(x.r - 1) || R.get(x.r)).ch.find(c => c[0] === se.target);
				if (tc && cheb([tc[3], tc[4]], x.to) <= 1) focus++;
			}
		}
		if (focus > 0) s.stunFocus++;
		if (evs.some(x => x.k === 'Death' && x.who === se.target && x.r >= se.r && x.r <= se.lost + 2)) s.stunKill++;
	}
}

const pct = (a, b) => b ? (100 * a / b).toFixed(0) + '%' : '-';
console.log('files', files.length);
for (const side of ['us', 'them']) {
	const g = G[side];
	console.log(`\n== ${side}: games ${g.games} aliveTurns/game ${(g.aliveTurns / g.games).toFixed(0)} chan ${(g.chanTurns / g.games).toFixed(0)} stunned ${((g.stunnedTurns || 0) / g.games).toFixed(1)} rollover ${((g.rollTurns || 0) / g.games).toFixed(1)} enemy<=9 turns ${((g.turnsEnemy9 || 0) / g.games).toFixed(0)} | wards ${((g.wards || 0) / g.games).toFixed(1)} locks ${((g.locks || 0) / g.games).toFixed(2)} consumable ${((g.consumable || 0) / g.games).toFixed(2)} tp ${((g.tpChannel || 0) / g.games).toFixed(2)} deaths ${((g.deaths || 0) / g.games).toFixed(1)} bagLost ${((g.bagLost || 0) / g.games).toFixed(0)}`);
	for (const b of ['d5-6', 'd7-9']) console.log(`held spells, nearest enemy ${b}: ${g['held_' + b] || 0} turns, exchange with an enemy champion within 3r ${pct(g['heldF3_' + b] || 0, g['held_' + b] || 0)}, within 8r ${pct(g['heldF_' + b] || 0, g['held_' + b] || 0)}`);
	for (const b of ['d5-6', 'd7-9']) console.log(`  by action ${b}: ` + ['atk', 'move', 'idle'].map(a => `${a} ${g['heldAct_' + a + '_' + b] || 0} (fight<=8r ${pct(g['heldActF_' + a + '_' + b] || 0, g['heldAct_' + a + '_' + b] || 0)})`).join(', '));
	console.log('channelling enemy within 4 with spell ready: ' + Object.keys(g).filter(k => k.startsWith('chanOpp_')).map(k => `${k.slice(8)} ${g[k]} cast ${g['chanHit_' + k.slice(8)] || 0}`).join(', '));
	const rows = Object.entries(S).filter(([k]) => k.startsWith(side + '|')).sort();
	for (const [k, s] of rows) {
		const kind = k.split(':')[1];
		const n = g.games;
		let line = `${k.slice(side.length + 1).padEnd(22)} turns ${String(s.turns).padStart(6)} ready ${pct(s.ready, s.turns).padStart(4)} casts/g ${(s.casts / n).toFixed(1).padStart(5)} util ${pct(s.casts * 8, s.turns).padStart(4)}`;
		const per = (x) => ((x || 0) / n).toFixed(1);
		if (RANGED_SPELL.has(kind)) line += ` on champ/g ${per(s.onChamp)} camp/g ${per(s.onCamp)} other/g ${per(s.other)} | wasted/g: champ-in-4 ${per(s.wasteChamp)} (atk ${per(s.wc_atk)} move ${per(s.wc_move)} idle ${per(s.wc_idle)}) camp-safe ${per(s.wasteCampSafe)} (atk ${per(s.ws_atk)} move ${per(s.ws_move)} idle ${per(s.ws_idle)}) camp-enemy<=9 ${per(s.wasteCampNear)} [fight within 8r: ${pct(s.heldFight || 0, s.heldN || 0)}] no-target ${per(s.readyNoTarget)} | champ-in-4 & exchange this/next round ${per(s.fightIdleEx)}`;
		if (STUN.has(kind)) line += ` | stuns on champs: before-target-acts ${s.stunBefore} after ${s.stunAfter} on-channel ${s.stunChannel} followed-up ${s.stunFocus} kill<=2r ${s.stunKill}`;
		if (kind === 'reset') line += ` | atk-turns-with-reset-ready ${s.atkTurns} missed ${s.missedReset} proper(atk-reset-atk) ${s.properReset} reset-first ${s.resetBeforeAtk} no-follow ${s.resetNoFollow}`;
		if (kind === 'dash') line += ` | near-enemy(<=6) ${s.dashCombat}`;
		if (kind === 'shield') line += ` | casts-hit-within-5r ${s.shieldHitWin}/${s.casts} hits-absorbed-window ${s.shieldHitsIn} | ready-not-cast turns ${s.shieldIdle} of which hit this/next round ${s.readyHit}`;
		console.log(line);
	}
}
