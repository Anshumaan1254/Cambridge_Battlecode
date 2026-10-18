// Agent fight: the TK (FIGHT_TRACE) + FC (XM_TRACE) lines of the 12 rounds before each team-A death. SHOW=1 node tools/analysis/fight_tk.mjs REPLAY...
import fs from 'fs';
import { decode, unwrapReplay, CHAMP } from '../replay/decode.mjs';
const files = process.argv.slice(2).filter(a => a.endsWith('.repl26a'));
const PATH = ['?', 'fight', 'cflee', 'safety', 'trib', 'home', 'shop', 'alert', 'farm'];
const TASK = ['none', 'farm', 'cap', 'wait', 'trib', 'home', 'fight', 'flee'];
const cnt = {}; const add = (k, v) => { cnt[k] = cnt[k] || {}; cnt[k][v] = (cnt[k][v] || 0) + 1; };
for (const f of files) {
	const buf = fs.readFileSync(f);
	const text = unwrapReplay(buf, 'team-a.stdout').toString('latin1').replace(/\0/g, '');
	const tk = new Map(), fc = new Map();
	for (const l of text.split('\n')) {
		if (!l.startsWith('TK ') && !l.startsWith('FC ')) continue;
		const o = {}; for (const m of l.matchAll(/(\w+)=([-\d.]+)/g)) o[m[1]] = Number(m[2]);
		(l[0] === 'T' ? tk : fc).set(`${o.r}:${o.ty}`, o);
	}
	const d = await decode(unwrapReplay(buf), { every: 50 });
	const seen = new Set();
	for (const e of d.events.filter((e) => e.k === 'Death' && e.team === 0)) {
		const ty = CHAMP.indexOf(e.champ);
		const parts = [];
		let firstDz = null, lastOut = null;
		for (let r = e.r - 12; r < e.r; ++r) {
			const o = tk.get(`${r}:${ty}`); if (!o) continue;
			const c = fc.get(`${r}:${ty}`);
			parts.push(`${r}:${PATH[o.path]}${o.dz ? '*' : ''}/e${o.ed}/${Math.round(100 * o.hp / o.mhp)}${c ? '/a' + c.adv.toFixed(2) : ''}`);
			if (o.dz && firstDz === null) firstDz = o; if (!o.dz) { lastOut = o; firstDz = null; }
		}
		if (process.env.SHOW) console.log(f.split('/').slice(-2, -1)[0], e.champ, 'r' + e.r, parts.join(' '));
		if (lastOut) add('last out-of-reach path', PATH[lastOut.path] + (lastOut.path === 8 ? '' : ''));
		else add('last out-of-reach path', 'none in 12');
	}
}
for (const [k, v] of Object.entries(cnt)) console.log(k.padEnd(24), Object.entries(v).sort((a, b) => b[1] - a[1]).map(([a, b]) => `${a} ${b}`).join(', '));
