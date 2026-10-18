// Farming economy of both teams in ladder replays (or local ones): when each body first captures, how often,
// how many captures are split with an ally, deaths, recalls, shops, items, and the banked / camp-gem curves.
//   node tools/analysis/ladder_econ.mjs REPLAY... [--bodies] [--json out.json]
// Team 0 is side A. Item names: <family><stat><S|E>, families M(onster) P(ower) D(urability) T(reasure) J(ungle)
// H(ome) B(ruiser), stats s(trength) f(ocus) h(ealth); e.g. MsE = Monster emblem of strength, Pf4 = 4 power focus shards.
import fs from 'fs';
import path from 'path';
import { decode } from '../replay/decode.mjs';
const args = process.argv.slice(2);
const showBodies = args.includes('--bodies');
const jsonOut = args.includes('--json') ? args[args.indexOf('--json') + 1] : null;
const FAM = 'MPDTJHB', ST = 'sfh';
const itemName = ([k, q]) => `${FAM[Math.floor(k / 6)]}${ST[Math.floor(k / 2) % 3]}${k % 2 ? 'E' : ''}${q > 1 || k % 2 === 0 ? q : ''}`;
const at = (rounds, r) => rounds[Math.min(rounds.length - 1, Math.max(0, r - 1))];
const all = [];
for (const f of args.filter((a) => a.endsWith('.repl26a'))) {
	const d = await decode(fs.readFileSync(f), { every: 1 });
	const name = path.basename(f, '.repl26a');
	const R = d.rounds, last = R.at(-1).r;
	const bodies = d.meta.bodies.map((b) => ({ ...b, caps: [], split: 0, deaths: 0, dead: 0, recalls: 0, shops: 0, firstShop: 0, gemsLost: 0 }));
	const caps = d.events.filter((e) => e.k === 'CaptureGems');
	for (const e of caps) {
		const b = bodies[e.who];
		const shared = caps.some((o) => o !== e && o.r === e.r && o.team === e.team && Math.max(Math.abs(o.at[0] - e.at[0]), Math.abs(o.at[1] - e.at[1])) <= 6
			&& !(b.type === 'Cassi' && bodies[o.who].type === 'Issac') && !(b.type === 'Issac' && bodies[o.who].type === 'Cassi'));
		b.caps.push([e.r, e.gems, e.gold]);
		if (shared) b.split++;
	}
	for (const e of d.events) {
		const b = bodies[e.who];
		if (!b) continue;
		if (e.k === 'Death') { b.deaths++; b.gemsLost += e.bag || 0; }
		if (e.k === 'Recall') b.recalls++;
		if (e.k === 'Shop') { b.shops++; if (!b.firstShop) b.firstShop = e.r; }
	}
	for (const r of R) for (const c of r.ch) if (!c[7]) bodies[c[0]].dead++;
	const team = [0, 1].map((t) => {
		const tb = bodies.filter((b) => b.team === t);
		const campGems = (r) => caps.filter((e) => e.team === t && e.r <= r).reduce((s, e) => s + e.gems, 0);
		const reach = (g) => { const x = R.find((r) => r.sub[t] >= g); return x ? x.r : '-'; };
		return {
			draft: d.meta.drafts[t].join(','), banked: R.at(-1).sub[t],
			sub100: at(R, 100).sub[t], sub200: at(R, 200).sub[t], sub300: at(R, 300).sub[t],
			camp100: campGems(100), camp200: campGems(200), camp300: campGems(300), campAll: campGems(1e9),
			r250: reach(250), r500: reach(500), r750: reach(750),
			firstCap: tb.map((b) => (b.caps[0] ? b.caps[0][0] : '-')).join('/'),
			caps: tb.reduce((s, b) => s + b.caps.length, 0), split: tb.reduce((s, b) => s + b.split, 0),
			deaths: tb.reduce((s, b) => s + b.deaths, 0), deadShare: tb.reduce((s, b) => s + b.dead, 0) / (tb.length * R.length),
			recalls: tb.reduce((s, b) => s + b.recalls, 0), gemsLost: tb.reduce((s, b) => s + b.gemsLost, 0),
			firstShop: tb.map((b) => b.firstShop || '-').join('/'),
			items150: tb.map((b) => `${b.type}:${(at(R, 150).ch[b.index][11] || []).map(itemName).join('+')}`),
			itemsEnd: tb.map((b) => `${b.type}:${(R.at(-1).ch[b.index][11] || []).map(itemName).join('+')}`),
		};
	});
	const res = { name, last, outcome: d.meta.outcome, bodies, team };
	all.push(res);
	console.log(`\n== ${name}: r${last}, banked ${team[0].banked}-${team[1].banked}`);
	for (const t of [0, 1]) {
		const x = team[t];
		console.log(` ${t ? 'B' : 'A'} ${x.draft}`);
		console.log(`   banked r100/200/300 ${x.sub100}/${x.sub200}/${x.sub300}  reach 250/500/750 r${x.r250}/r${x.r500}/r${x.r750}  camp gems r100/200/300/all ${x.camp100}/${x.camp200}/${x.camp300}/${x.campAll}`);
		console.log(`   first capture ${x.firstCap}  captures ${x.caps} (split ${x.split})  deaths ${x.deaths} (dead ${(100 * x.deadShare).toFixed(0)}%, bags lost ${x.gemsLost})  recalls ${x.recalls}  first shop ${x.firstShop}`);
		console.log(`   items r150 ${x.items150.join('  ')}`);
		console.log(`   items end  ${x.itemsEnd.join('  ')}`);
		if (showBodies) for (const b of bodies.filter((b) => b.team === t)) console.log(`     ${b.type.padEnd(8)} caps ${b.caps.map(([r, g]) => `r${r}:${g}`).join(' ')}`);
	}
}
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(all));
