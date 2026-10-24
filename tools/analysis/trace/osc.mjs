// Oscillation windows (behav.mjs definition) joined with the LEGEND_TRACE task / target of each round: what the body was doing.
import fs from 'node:fs';
import path from 'node:path';
const { decode, unwrapReplay } = await import('../../replay/decode.mjs');
const { mapGrid } = await import('../stuck.mjs');
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const TASK = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee'];
const dir = process.argv[2];
const byKey = new Map(), ex = new Map();
let nwin = 0, nrounds = 0;
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a'))) {
	const raw = fs.readFileSync(path.join(dir, f));
	const ours = /_B\.repl26a$/.test(f) ? 1 : 0;
	let text = '';
	try { text = unwrapReplay(raw, ours ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'); } catch { continue; }
	const tr = new Map(); // type:round -> {task,g}
	for (let l of text.split('\n')) {
		l = l.replace(/\x00/g, '').trim();
		const m = l.match(/^T r=(\d+) (\d+) task=(\d+) g=(-?\d+)/);
		if (m) tr.set(m[2] + ':' + m[1], { task: +m[3], g: +m[4] });
	}
	const rep = unwrapReplay(raw);
	const d = await decode(rep);
	const grid = await mapGrid(rep);
	const byRound = new Map(d.rounds.map((r) => [r.r, r]));
	const act = new Set(), chan = new Map();
	for (const e of d.events) {
		if (e.who === undefined) continue;
		if (e.k === 'Attack' || (e.k === 'Cast ability' && e.ability !== 6)) act.add(e.r + ':' + e.who);
		if (e.k === 'Recall' || e.k === 'Submit gems' || e.k === 'Teleport channel') chan.set(e.who, [...(chan.get(e.who) || []), e.r]);
	}
	const bodies = d.meta.bodies.filter((b) => b.team === ours);
	const enemies = d.meta.bodies.filter((b) => b.team !== ours).map((b) => b.index);
	const typeIdx = (name) => ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'].indexOf(name);
	for (const b of bodies) {
		const ti = typeIdx(b.type);
		const hist = [];
		let prev = null;
		const ch = chan.get(b.index) || [];
		for (let r = 1; r <= d.meta.finalRound; r++) {
			const s = byRound.get(r); if (!s) continue;
			const c = s.ch.find((q) => q[0] === b.index); if (!c) continue;
			const alive = c[7] === 1, pos = [c[3], c[4]];
			let near = false;
			for (const k of enemies) { const e = s.ch.find((q) => q[0] === k); if (e && e[7] && cheb([e[3], e[4]], pos) <= 5) { near = true; break; } }
			const onSpawn = alive && grid.spawn[ours][pos[1] * grid.w + pos[0]] === 1;
			const lastChan = Math.max(-99, ...ch.filter((x) => x <= r));
			const moved = alive && prev && prev.alive && (pos[0] !== prev.pos[0] || pos[1] !== prev.pos[1]);
			const elig = alive && !onSpawn && !near && !act.has(r + ':' + b.index) && r - lastChan > 5;
			hist.push({ r, pos, elig, moved, t: tr.get(ti + ':' + r) });
			prev = { alive, pos };
		}
		let i = 0;
		while (i + 10 <= hist.length) {
			const w = hist.slice(i, i + 10);
			if (w.every((x) => x.elig) && w.filter((x) => x.moved).length >= 6 && cheb(w[0].pos, w[9].pos) <= 1) {
				let j = i + 10;
				while (j < hist.length && hist[j].elig && cheb(hist[j].pos, w[0].pos) <= 2) j++;
				const ws = hist.slice(i, j);
				const tasks = [...new Set(ws.filter((x) => x.t).map((x) => TASK[x.t.task]))].sort().join('+');
				const tg = new Set(ws.filter((x) => x.t && x.t.g >= 0).map((x) => x.t.g)).size;
				const key = `${tasks} targets=${Math.min(tg, 3)}${tg >= 3 ? '+' : ''} ${b.type}`;
				byKey.set(key, (byKey.get(key) || 0) + (j - i));
				if (!ex.has(key)) ex.set(key, `${f} r${hist[i].r}-${hist[j - 1].r} (${w[0].pos})`);
				nwin++, nrounds += j - i;
				i = j;
			} else i++;
		}
	}
}
console.log(`windows ${nwin}, body-rounds ${nrounds}`);
for (const [k, v] of [...byKey].sort((a, b) => b[1] - a[1]).slice(0, 30)) console.log(`  ${k.padEnd(48)} ${v}  ${ex.get(k)}`);
