// Target switches (SW trace lines): per game, A-B-A returns within 20 rounds, the reason the old target was dropped (why code).
import fs from 'node:fs';
import path from 'node:path';
const { unwrapReplay } = await import('../../replay/decode.mjs');
const dir = process.argv[2];
let games = 0, sw = 0, aba = 0;
const why = new Map(), whyAba = new Map();
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.repl26a'))) {
	let text = '';
	try { text = unwrapReplay(fs.readFileSync(path.join(dir, f)), /_B\.repl26a$/.test(f) ? 'team-b.stdout' : 'team-a.stdout').toString('latin1'); } catch { continue; }
	games++;
	const hist = new Map(); // type -> [{r, old, new}]
	for (let l of text.split('\n')) {
		l = l.replace(/\x00/g, '').trim();
		const m = l.match(/^SW r=(\d+) (\d+) old=(-?\d+) new=(-?\d+) sold=(-?[\d.]+) snew=(-?[\d.]+) .* why=(\d+)/);
		if (!m) continue;
		const r = +m[1], ty = m[2], o = +m[3], n = +m[4], w = (+m[5] < 0 ? 'why' + m[7] : 'better');
		sw++;
		why.set(w, (why.get(w) || 0) + 1);
		const H = hist.get(ty) || [];
		// A-B-A: this switch goes back to a target we left within the last 20 rounds
		if (H.some((h) => h.old === n && r - h.r <= 20)) { aba++; whyAba.set(w, (whyAba.get(w) || 0) + 1); }
		H.push({ r, old: o, new: n });
		hist.set(ty, H.filter((h) => r - h.r <= 40));
	}
}
console.log(`games ${games}, target switches ${sw} (${(sw / games).toFixed(1)} a game), A-B-A returns within 20 rounds ${aba} (${(100 * aba / sw).toFixed(1)}%)`);
console.log('old target dropped because:', [...why].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', '));
console.log('A-B-A returns, old dropped because:', [...whyAba].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', '));
