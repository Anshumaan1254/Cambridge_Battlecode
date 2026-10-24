// IDLE trace lines (god14 LEGEND_TRACE builds) from kept replays: idle turns and idle streaks (>= 4 rounds) by code point.
import fs from 'node:fs';
import path from 'node:path';
const { unwrapReplay } = await import('../../replay/decode.mjs');
const dir = process.argv[2];
const turns = new Map(), streaks = new Map(), streakRounds = new Map();
let total = 0, idleFar = 0;
const examples = new Map();
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a'))) {
	const raw = fs.readFileSync(path.join(dir, f));
	const side = /_B\.repl26a$/.test(f) ? 'team-b.stdout' : 'team-a.stdout';
	let text = '';
	try { text = unwrapReplay(raw, side).toString('latin1'); } catch { continue; }
	const last = new Map(); // type -> {r, key, start}
	for (let line of text.split('\n')) {
		line = line.replace(/\x00/g, '').trim();
		if (line.startsWith('T r=')) total++;
		const m = line.match(/^IDLE r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((-?\d+),(-?\d+)\) path=(\d+) at=(\d+) mf=(\d+) near=(-?\d+)/);
		if (!m) continue;
		const [_, r, ty, task, g, x, y, p, at, mf, near] = m.map((v, i) => (i ? +v : v));
		if (near <= 5) continue;
		idleFar++;
		const key = `path=${p} task=${task} at=${at} mf=${mf > 0 ? 1 : 0}`;
		turns.set(key, (turns.get(key) || 0) + 1);
		const L = last.get(ty);
		if (L && L.r === r - 1) { L.r = r; L.len++; }
		else {
			if (L && L.len >= 4) { streaks.set(L.key, (streaks.get(L.key) || 0) + 1); streakRounds.set(L.key, (streakRounds.get(L.key) || 0) + L.len); if (!examples.has(L.key) || Math.random() < 0.2) examples.set(L.key, `${f} t${L.ty} r${L.start}-${L.r} ${L.pos}`); }
			last.set(ty, { r, len: 1, key, start: r, ty, pos: `(${x},${y}) g${g}` });
		}
	}
	for (const L of last.values()) if (L.len >= 4) { streaks.set(L.key, (streaks.get(L.key) || 0) + 1); streakRounds.set(L.key, (streakRounds.get(L.key) || 0) + L.len); }
}
console.log(`T lines ${total}, idle turns with no enemy within 5: ${idleFar} (${(100 * idleFar / total).toFixed(1)}%)`);
console.log('idle turns by point (top 25):');
for (const [k, v] of [...turns].sort((a, b) => b[1] - a[1]).slice(0, 25)) console.log(`  ${k.padEnd(36)} ${v}`);
console.log('idle streaks >= 4 rounds by first point (top 25): streaks, rounds, example');
for (const [k, v] of [...streakRounds].sort((a, b) => b[1] - a[1]).slice(0, 25)) console.log(`  ${k.padEnd(36)} ${streaks.get(k)} ${v}  ${examples.get(k) || ''}`);
