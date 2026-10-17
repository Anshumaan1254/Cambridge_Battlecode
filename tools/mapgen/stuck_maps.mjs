// Stress maps for the stuck-champion detector (tools/analysis/stuck.mjs): symmetric maps full of 1-tile
// corridors, dead ends, walled pockets around camps and altars (one-tile doors), camps standing in corridors,
// hole lines with single-tile bridges, bushes in corridors, and narrow gaps between camps and walls.
// Usage: node tools/mapgen/stuck_maps.mjs [outDir=maps/stuck] [count=8] [seed=7]
import fs from 'node:fs';
import path from 'node:path';
import { loadEngine, Builder, SYM, CAMP } from './engine.mjs';

const [outDir = 'maps/stuck', countArg = '8', seedArg = '7'] = process.argv.slice(2);
let seed = Number(seedArg) >>> 0 || 7;
const rnd = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed / 4294967296; };
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];

function mirror(sym, w, h, x, y) {
	if (sym === SYM.horizontal) return [w - 1 - x, y];
	if (sym === SYM.vertical) return [x, h - 1 - y];
	return [w - 1 - x, h - 1 - y];
}
function inHalfA(sym, w, h, x, y, margin = 1) {
	if (sym === SYM.horizontal) return x < Math.floor(w / 2) - margin;
	if (sym === SYM.vertical) return y < Math.floor(h / 2) - margin;
	return (x + y) < (w + h) / 2 - 1 - margin;
}

// tile codes: 0 ground, 1 wall, 2 bush, 3 hole, 4 altar, 5 camp, 6 spawn, 7 reserved ground (no terrain)
function makeMap(E, style, idx) {
	const size = style.size;
	const w = Math.max(30, Math.min(100, size + ri(-3, 3)));
	const h = Math.max(30, Math.min(100, size + ri(-3, 3)));
	const sym = style.sym ?? pick([SYM.horizontal, SYM.vertical, SYM.rot180]);
	const champs = style.champs ?? pick([3, 4, 5]);
	const g = new Uint8Array(w * h);
	const inb = (x, y) => x >= 0 && y >= 0 && x < w && y < h;
	const at = (x, y) => g[y * w + x];
	const setBoth = (x, y, v) => { if (!inb(x, y)) return; const [mx, my] = mirror(sym, w, h, x, y); g[y * w + x] = v; g[my * w + mx] = v; };
	const free = (x, y) => inb(x, y) && at(x, y) === 0;
	const half = (x, y, m = 1) => inHalfA(sym, w, h, x, y, m);

	// Spawn with a reserved ring.
	const sw = 3, sh = 3;
	let sx, sy;
	if (sym === SYM.horizontal) { sx = 2; sy = ri(4, h - sh - 4); }
	else if (sym === SYM.vertical) { sy = 2; sx = ri(4, w - sw - 4); }
	else { sx = 2; sy = 2 + ri(0, Math.floor(h / 6)); }
	for (let y = sy - 1; y <= sy + sh; y++) for (let x = sx - 1; x <= sx + sw; x++) if (inb(x, y)) setBoth(x, y, 7);
	for (let y = sy; y < sy + sh; y++) for (let x = sx; x < sx + sw; x++) setBoth(x, y, 6);

	const camps = [], altars = [];
	const rectFree = (x0, y0, x1, y1) => {
		for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (!inb(x, y) || !half(x, y, 0) || at(x, y) !== 0) return false;
		return true;
	};
	// A walled room with 1-tile doors; inside a camp group or an altar (pockets near camps and altars).
	const room = (rw, rh, doors, content) => {
		for (let t = 0; t < 300; t++) {
			const x0 = ri(1, w - rw - 2), y0 = ri(1, h - rh - 2), x1 = x0 + rw - 1, y1 = y0 + rh - 1;
			if (!rectFree(x0 - 1, y0 - 1, x1 + 1, y1 + 1)) continue;
			const border = [];
			for (let x = x0; x <= x1; x++) border.push([x, y0], [x, y1]);
			for (let y = y0 + 1; y < y1; y++) border.push([x0, y], [x1, y]);
			for (const [x, y] of border) setBoth(x, y, 1);
			// Doors: not on corners.
			const sides = border.filter(([x, y]) => !((x === x0 || x === x1) && (y === y0 || y === y1)));
			for (let k = 0; k < doors; k++) { const [x, y] = pick(sides); setBoth(x, y, 7); }
			const ix0 = x0 + 1, iy0 = y0 + 1, ix1 = x1 - 1, iy1 = y1 - 1;
			if (content === 'altar') {
				const ax = ri(ix0, ix1), ay = ri(iy0, iy1);
				setBoth(ax, ay, 4); altars.push([ax, ay]);
			} else {
				// 1-3 camps in a row inside, leaving at least one free tile next to a door side
				const n = Math.min(content.n, (ix1 - ix0 + 1));
				const cy = ri(iy0, iy1), cx = ri(ix0, Math.max(ix0, ix1 - n + 1));
				for (let k = 0; k < n; k++) if (at(cx + k, cy) === 0) { setBoth(cx + k, cy, 5); camps.push([content.type, cx + k, cy]); }
			}
			return true;
		}
		return false;
	};
	// Corridor: two parallel wall lines with a 1-tile lane between; sometimes a camp standing in the lane.
	const corridor = (len, campChance, bushChance) => {
		for (let t = 0; t < 300; t++) {
			const horiz = rnd() < 0.5;
			const x0 = ri(1, w - 2 - (horiz ? len : 3)), y0 = ri(1, h - 2 - (horiz ? 3 : len));
			const x1 = horiz ? x0 + len - 1 : x0 + 2, y1 = horiz ? y0 + 2 : y0 + len - 1;
			if (!rectFree(x0, y0, x1, y1)) continue;
			for (let k = 0; k < len; k++) {
				if (horiz) { setBoth(x0 + k, y0, 1); setBoth(x0 + k, y0 + 2, 1); if (rnd() < bushChance) setBoth(x0 + k, y0 + 1, 2); else setBoth(x0 + k, y0 + 1, 7); }
				else { setBoth(x0, y0 + k, 1); setBoth(x0 + 2, y0 + k, 1); if (rnd() < bushChance) setBoth(x0 + 1, y0 + k, 2); else setBoth(x0 + 1, y0 + k, 7); }
			}
			if (rnd() < campChance) {
				const k = ri(2, len - 3);
				const [cx, cy] = horiz ? [x0 + k, y0 + 1] : [x0 + 1, y0 + k];
				setBoth(cx, cy, 5); camps.push([pick([CAMP.wolf, CAMP.gem, CAMP.gold]), cx, cy]);
			}
			// A dead end: close one end.
			if (rnd() < 0.35) { if (horiz) setBoth(x0, y0 + 1, 1); else setBoth(x0 + 1, y0, 1); }
			return true;
		}
		return false;
	};
	// Comb: a wall spine with teeth, making 1-wide dead-end pockets; camps at the back of some pockets.
	const comb = (teeth, depth) => {
		for (let t = 0; t < 300; t++) {
			const horiz = rnd() < 0.5;
			const span = teeth * 2 + 1;
			const x0 = ri(1, w - 2 - (horiz ? span : depth + 1)), y0 = ri(1, h - 2 - (horiz ? depth + 1 : span));
			const x1 = horiz ? x0 + span - 1 : x0 + depth, y1 = horiz ? y0 + depth : y0 + span - 1;
			if (!rectFree(x0, y0, x1, y1)) continue;
			for (let k = 0; k < span; k++) {
				if (horiz) setBoth(x0 + k, y0, 1); else setBoth(x0, y0 + k, 1);
				if (k % 2 === 0) for (let d = 1; d <= depth; d++) { if (horiz) setBoth(x0 + k, y0 + d, 1); else setBoth(x0 + d, y0 + k, 1); }
				else {
					for (let d = 1; d <= depth; d++) { if (horiz) setBoth(x0 + k, y0 + d, 7); else setBoth(x0 + d, y0 + k, 7); }
					if (rnd() < 0.3) { const [cx, cy] = horiz ? [x0 + k, y0 + 1] : [x0 + 1, y0 + k]; setBoth(cx, cy, 5); camps.push([pick([CAMP.gem, CAMP.wolf]), cx, cy]); }
				}
			}
			return true;
		}
		return false;
	};
	// Hole line with single-tile bridges.
	const holeLine = (len) => {
		for (let t = 0; t < 200; t++) {
			const horiz = rnd() < 0.5;
			const x0 = ri(1, w - 2 - (horiz ? len : 0)), y0 = ri(1, h - 2 - (horiz ? 0 : len));
			if (!rectFree(x0, y0, horiz ? x0 + len - 1 : x0, horiz ? y0 : y0 + len - 1)) continue;
			const gap = ri(1, len - 2);
			for (let k = 0; k < len; k++) if (k !== gap) { if (horiz) setBoth(x0 + k, y0, 3); else setBoth(x0, y0 + k, 3); }
			return true;
		}
		return false;
	};
	// Open-ground camp group hugging a wall (narrow gap between camps and wall).
	const wallHug = (type, n) => {
		for (let t = 0; t < 300; t++) {
			const x0 = ri(2, w - n - 3), y0 = ri(2, h - 5);
			if (!rectFree(x0 - 1, y0 - 1, x0 + n, y0 + 3)) continue;
			for (let k = -1; k <= n; k++) setBoth(x0 + k, y0, 1);
			for (let k = 0; k < n; k++) { setBoth(x0 + k, y0 + 2, 5); camps.push([type, x0 + k, y0 + 2]); }
			setBoth(x0 - 1, y0 + 1, 1); // a pocket between the wall and the camps, open on one side
			return true;
		}
		return false;
	};

	const area = w * h;
	const scale = Math.sqrt(area / 2500);
	// Altars: one in a pocket near-ish spawn, one in the open (keep the ring free).
	room(5, 5, 1, 'altar');
	if (style.altars !== 1) room(4, 4, 2, 'altar');
	for (let i = 0; i < Math.round(style.rooms * scale); i++) room(ri(4, 6), ri(4, 5), ri(1, 2), { type: pick([CAMP.gem, CAMP.wolf, CAMP.gem, CAMP.elk, CAMP.gold]), n: ri(1, 3) });
	for (let i = 0; i < Math.round(style.corridors * scale); i++) corridor(ri(6, 14), style.corrCamp ?? 0.4, style.bush ?? 0.15);
	for (let i = 0; i < Math.round(style.combs * scale); i++) comb(ri(2, 4), ri(2, 4));
	for (let i = 0; i < Math.round(style.holes * scale); i++) holeLine(ri(5, 12));
	for (let i = 0; i < Math.round(style.hugs * scale); i++) wallHug(pick([CAMP.wolf, CAMP.gem, CAMP.elk]), ri(2, 3));
	// Extra open camps so the map has enough to farm.
	for (let i = 0; i < Math.round(style.open * scale); i++) {
		for (let t = 0; t < 200; t++) {
			const x = ri(2, w - 3), y = ri(2, h - 3);
			if (!rectFree(x - 1, y - 1, x + 1, y + 1)) continue;
			setBoth(x, y, 5); camps.push([pick([CAMP.gem, CAMP.wolf, CAMP.gold]), x, y]);
			break;
		}
	}
	if (altars.length === 0 || camps.length < 4) return null;

	// Connectivity with live camps as obstacles: every camp neighbourhood and altar reachable from spawn.
	const passable = (x, y) => inb(x, y) && ![1, 3, 4, 5].includes(at(x, y));
	const seen = new Uint8Array(w * h);
	const q = [[sx, sy]];
	seen[sy * w + sx] = 1;
	while (q.length) {
		const [x, y] = q.pop();
		for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
			const nx = x + dx, ny = y + dy;
			if (passable(nx, ny) && !seen[ny * w + nx]) { seen[ny * w + nx] = 1; q.push([nx, ny]); }
		}
	}
	const touched = (x, y) => { for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (inb(x + dx, y + dy) && seen[(y + dy) * w + x + dx]) return true; return false; };
	const [ex, ey] = mirror(sym, w, h, sx, sy);
	if (!seen[ey * w + ex]) return null;
	for (const [, x, y] of camps) { if (!touched(x, y)) return null; const [mx, my] = mirror(sym, w, h, x, y); if (!touched(mx, my)) return null; }
	for (const [x, y] of altars) if (!touched(x, y)) return null;

	const b = new Builder(E, w, h, sym);
	try {
		b.champs(champs);
		b.spawn(sx, sy, sx + sw, sy + sh);
		for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
			const v = at(x, y);
			if (v === 1) b.wall(x, y); else if (v === 2) b.bush(x, y); else if (v === 3) b.hole(x, y);
		}
		for (const [x, y] of altars) if (half(x, y, 0)) b.altar(x, y);
		for (const [t, x, y] of camps) if (half(x, y, 0)) b.camp(t, x, y);
		const bytes = b.encode();
		const name = `stk${String(idx).padStart(2, '0')}_${style.name}_${w}x${h}_${['H', 'V', 'R'][sym]}_c${champs}`;
		return { name, bytes, info: { w, h, sym, champs, camps: camps.length, altars: altars.length } };
	} catch (e) {
		return null;
	} finally { b.destroy(); }
}

const STYLES = [
	{ name: 'corr', size: 44, rooms: 3, corridors: 8, combs: 2, holes: 1, hugs: 2, open: 3 },
	{ name: 'pocket', size: 50, rooms: 6, corridors: 3, combs: 3, holes: 0, hugs: 3, open: 2 },
	{ name: 'maze', size: 60, rooms: 4, corridors: 12, combs: 4, holes: 2, hugs: 2, open: 3, bush: 0.3 },
	{ name: 'holes', size: 48, rooms: 3, corridors: 4, combs: 1, holes: 8, hugs: 2, open: 4 },
	{ name: 'bigcorr', size: 92, rooms: 4, corridors: 8, combs: 3, holes: 2, hugs: 3, open: 4, champs: 5 },
	{ name: 'small', size: 32, rooms: 3, corridors: 5, combs: 2, holes: 1, hugs: 2, open: 2, altars: 1 },
	{ name: 'comb', size: 56, rooms: 3, corridors: 4, combs: 7, holes: 1, hugs: 4, open: 2 },
	{ name: 'bigpocket', size: 80, rooms: 8, corridors: 6, combs: 4, holes: 3, hugs: 3, open: 3, champs: 4 },
];

const E = await loadEngine();
fs.mkdirSync(outDir, { recursive: true });
const want = Number(countArg);
let made = 0, attempts = 0;
const index = [];
while (made < want && attempts < want * 400) {
	attempts++;
	const m = makeMap(E, STYLES[made % STYLES.length], made);
	if (!m) continue;
	fs.writeFileSync(path.join(outDir, m.name + '.map26a'), m.bytes);
	index.push({ name: m.name, ...m.info });
	made++;
}
console.log(`made ${made} maps in ${attempts} attempts`);
for (const m of index) console.log(m.name, JSON.stringify(m));
