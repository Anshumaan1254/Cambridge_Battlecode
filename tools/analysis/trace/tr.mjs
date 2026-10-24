// Print a body's trace lines (T, SW, IDLE, UNSTICK, B, GW, ...) for a round window, plus nearby enemies from the replay.
import fs from 'node:fs';
const { decode, unwrapReplay } = await import('../../replay/decode.mjs');
const [file, type, r0, r1] = process.argv.slice(2);
const raw = fs.readFileSync(file);
const ours = /_B\.repl26a$/.test(file) ? 1 : 0;
const text = unwrapReplay(raw, ours ? 'team-b.stdout' : 'team-a.stdout').toString('latin1');
const d = await decode(unwrapReplay(raw));
const byRound = new Map(d.rounds.map((r) => [r.r, r]));
const names = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'];
for (let l of text.split('\n')) {
	l = l.replace(/\x00/g, '').trim();
	const m = l.match(/^([A-Z]+) r=(\d+) (\d+) /);
	if (!m || m[3] !== type || +m[2] < +r0 || +m[2] > +r1) continue;
	let extra = '';
	if (m[1] === 'T') {
		const s = byRound.get(+m[2]);
		const me = s && s.ch.find((c) => c[1] === ours && names[c[2]] === names[+type]);
		if (s && me) extra = ' | ' + s.ch.filter((c) => c[1] !== ours && c[7]).map((c) => `${names[c[2]].slice(0, 4)}@${c[3]},${c[4]} d${Math.max(Math.abs(c[3] - me[3]), Math.abs(c[4] - me[4]))}`).filter((x) => +x.split(' d')[1] <= 12).join(' ');
	}
	console.log(l + extra);
}
