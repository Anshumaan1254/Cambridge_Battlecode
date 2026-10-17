// Turn fight-model logs (XML_LOG builds) into a labelled CSV for tools/ml/train.py.
//
// usage: node tools/ml/parse_logs.mjs OUT.csv DIR [DIR ...]
// Each DIR holds bench.py / run_games.py output (NAME_A.repl26a: our bot is team A; NAME_B: team B). For every
// "ML," line printed by our bot (one per combat() evaluation with an enemy within 9) it finds the body in the
// replay (team + champion type, position checked) and labels what happened in the next H = 12 rounds:
//   die      this body died                       kill   an enemy that was within 6 died
//   mykill   this body was credited a kill        adie   another ally that was within 6 died
//   hploss   health lost as a fraction of max (1 if it died)
//   bag      gems this body lost by dying         ebag   gems carried by the enemies that died (within 6)
// plus game id, body id and encounter id (a new encounter after 6 rounds without an evaluation).
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { decode } from '/home/user/Cambridge_Battlecode/tools/replay/decode.mjs';

const H = 12;
export const FIELDS = ('round,team,idx,type,x,y,hp,max_hp,str,focus,r_dmg,r_cc,r_aoe,r_reset,r_dash,can_attack,my_burst,' +
	'allies_near,a_hp,a_max,a_dps,backup,dead_allies,a_alive,' +
	'nE,their_hp,their_dps,incoming,stunners,e_max,e_min,e_reach,e_d3,e_dash,e_ranged,e_alive,' +
	'nearest,tgt_type,tgt_hp,tgt_max,tgt_d,tgt_gems,tgt_chan,e_gems,' +
	'killable,in_reach,chaser,chaser_dash,can_escape,t_die,dh,da,on_spawn,gems,gold,' +
	'adv_f,adv,t_kill_us,t_kill_them,fight_margin,fight_back_margin,iso_adv,stance,deficit,ours_g,theirs_g,fscale,dec').split(',');
const LABELS = ['game', 'opp', 'body', 'enc', 'die', 'kill', 'mykill', 'adie', 'hploss', 'bag', 'ebag', 'win', 'margin'];

function zipMember(buf, member) {
	const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
	let off = 0;
	while (off + 30 <= buf.length && dv.getUint32(off, true) === 0x04034b50) {
		const method = dv.getUint16(off + 8, true);
		const csize = dv.getUint32(off + 18, true);
		const nlen = dv.getUint16(off + 26, true), xlen = dv.getUint16(off + 28, true);
		const name = Buffer.from(buf.subarray(off + 30, off + 30 + nlen)).toString();
		const start = off + 30 + nlen + xlen;
		const data = buf.subarray(start, start + csize);
		if (name === member) return (method === 8 ? zlib.inflateRawSync(data) : Buffer.from(data)).toString();
		off = start + csize;
	}
	return '';
}

const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

async function parseGame(file, opp) {
	const buf = fs.readFileSync(file);
	const side = path.basename(file).replace(/\.repl26a$/, '').slice(-1); // our team: A -> 0, B -> 1
	const team = side === 'A' ? 0 : 1;
	const text = zipMember(buf, side === 'A' ? 'team-a.stdout' : 'team-b.stdout');
	const rows = [];
	for (const m of text.matchAll(/ML,([-0-9.,]+)/g)) {
		const v = m[1].split(',').map(Number);
		if (v.length === FIELDS.length) rows.push(v);
	}
	if (!rows.length) return [];
	const d = await decode(buf, { every: 1 });
	const byRound = new Map(d.rounds.map((r) => [r.r, r.ch]));
	const deaths = d.events.filter((e) => e.k === 'Death');
	const win = d.meta.outcome === team + 1 ? 1 : 0;
	const sub = d.meta.submitted || [0, 0];
	const margin = (sub[team] ?? 0) - (sub[1 - team] ?? 0);
	// body index by champion type on our team (our drafts never repeat a type)
	const bodies = d.meta.bodies.filter((b) => b.team === team);
	const CH = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'];
	const out = [];
	const lastEval = new Map();
	const encId = new Map();
	let badPos = 0;
	const gid = path.basename(path.dirname(file)) + '/' + path.basename(file);
	for (const v of rows) {
		const r = v[0], type = v[3];
		if (v[1] !== team) continue;
		const body = bodies.find((b) => b.type === CH[type]);
		if (!body) continue;
		const c = body.index;
		const snap = byRound.get(r - 1) || byRound.get(r);
		if (!snap) continue;
		const me = snap.find((q) => q[0] === c);
		if (!me) continue;
		if (cheb([me[3], me[4]], [v[4], v[5]]) > 1) badPos++;
		const myPos = [v[4], v[5]];
		const inWin = (e) => e.r >= r && e.r <= r + H;
		const myDeath = deaths.find((e) => e.who === c && inWin(e));
		const near = (q) => q[7] && cheb([q[3], q[4]], myPos) <= 6;
		const enemiesNear = snap.filter((q) => q[1] !== team && near(q)).map((q) => q[0]);
		const alliesNear = snap.filter((q) => q[1] === team && q[0] !== c && near(q)).map((q) => q[0]);
		const eDeaths = deaths.filter((e) => inWin(e) && enemiesNear.includes(e.who));
		const aDeaths = deaths.filter((e) => inWin(e) && alliesNear.includes(e.who));
		// kills credited: kill counter at the end of the window minus before
		const endSnap = byRound.get(Math.min(d.meta.finalRound, r + H)) || snap;
		const meEnd = endSnap.find((q) => q[0] === c) || me;
		let hpMin = me[5];
		for (let k = r; k <= r + H; k++) {
			const s = byRound.get(k);
			if (!s) continue;
			const q = s.find((x) => x[0] === c);
			if (q && q[7]) hpMin = Math.min(hpMin, q[5]);
		}
		const key = c;
		if (!lastEval.has(key) || r - lastEval.get(key) > 6) encId.set(key, (encId.get(key) || 0) + 1);
		lastEval.set(key, r);
		out.push([...v, gid, opp, c, encId.get(key), myDeath ? 1 : 0, eDeaths.length ? 1 : 0, meEnd[10] > me[10] ? 1 : 0, aDeaths.length ? 1 : 0,
			myDeath ? 1 : Math.max(0, (me[5] - hpMin) / Math.max(1, me[6])), myDeath ? myDeath.bag : 0,
			eDeaths.reduce((s, e) => s + (e.bag || 0), 0), win, margin]);
	}
	if (badPos > out.length * 0.05) console.error(`warning: ${gid}: ${badPos}/${out.length} rows with a position mismatch`);
	return out;
}

const [outFile, ...dirs] = process.argv.slice(2);
const lines = [[...FIELDS, ...LABELS].join(',')];
let games = 0;
for (const dir of dirs) {
	const opp = (path.basename(dir).match(/_vs_(.+?)(_\d+)?$/) || [null, path.basename(dir)])[1];
	for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.repl26a')).sort()) {
		const rows = await parseGame(path.join(dir, f), opp);
		for (const r of rows) lines.push(r.join(','));
		games++;
		console.error(`${dir}/${f}: ${rows.length} rows`);
	}
}
fs.writeFileSync(outFile, lines.join('\n') + '\n');
console.error(`${games} games, ${lines.length - 1} rows -> ${outFile}`);
