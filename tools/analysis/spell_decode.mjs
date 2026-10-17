// Copy of tools/replay/decode.mjs for tools/analysis/spell_usage.mjs: decode(buf, {endturns: true}) also keeps
// 'End turn' events (turn order inside a round), and every round snapshot champion row gets two extra
// fields: [12] stunned flag, [13] consumable counts. Library only (no CLI).
// Decode a CAMBC 2026a replay (.repl26a) into JSON using the engine wasm that ships with the visualiser.
//
//   node tools/replay/decode.mjs replay.repl26a [--out file.json] [--every N]
//
// Output: { meta, rounds: [ per-round snapshot ], events: [ action log ] }
//   meta    map size, drafts (both teams), outcome, final round, final submitted gems, camp list
//   rounds  one entry per round (state at the end of the round): submitted gems, every champion
//           (team, type, position, health, alive, gems carried, gold, kills, items), group rewards
//   events  every champion action step (move, attack, cast, recall, submit, shop, ward, capture...)
//           plus derived deaths (with the bag lost) and captures
//
// The snapshot layouts are the visualiser's own (PanelChrome module); the engine wasm is found in the
// cambc asset cache (run `cambc view` once if it is missing) or passed with CAMBC_ENGINE_WASM.
import fs from 'node:fs';
import path from 'node:path';
import { WASI } from 'node:wasi';
import zlib from 'node:zlib';

process.removeAllListeners('warning');

export const CHAMP = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'];
export const DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin'];
export const STEP = 'Phase.Respawn.Capture.Tick.Move.Attack.Cast ability.Input.End turn.Set priority..Recall.Submit gems.Shop.Place ward.Consumable.Cancel channel.Sandbox.Gems submitted.Draft champion.Place altar lock.Teleport channel.Teleport complete.Movement blocked.Resign.Sell item.Turn rollover.Bot error'.split('.');
export const CAMP = ['wolf', 'elk', 'gem', 'gold', 'monolith'];
const ITEM_COUNT = 42; // Hn.length in the visualiser (7 families x 3 stats x shard/emblem)

export function findEngineWasms() {
  if (process.env.CAMBC_ENGINE_WASM) return [process.env.CAMBC_ENGINE_WASM];
  const home = process.env.HOME || '/root';
  const root = process.env.CAMBC_CACHE || path.join(home, '.cache', 'cambc', 'assets');
  const found = [];
  if (fs.existsSync(root)) for (const hash of fs.readdirSync(root)) {
    for (const sub of ['visualiser', 'mapeditor']) {
      const dir = path.join(root, hash, sub, 'assets');
      if (!fs.existsSync(dir)) continue;
      for (const f of fs.readdirSync(dir)) if (/^v\d+_\d+_\d+-.*\.wasm$/.test(f)) found.push(path.join(dir, f));
    }
  }
  found.sort((a, b) => path.basename(b).localeCompare(path.basename(a), undefined, { numeric: true }));
  return found; // newest first
}

async function loadEngine(wasmPath) {
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  wasi.initialize(inst);
  const X = inst.exports;
  const out = X.Engine_Malloc(64);
  const dv = () => new DataView(X.memory.buffer);
  const cstr = (p) => { const u = new Uint8Array(X.memory.buffer); let s = ''; while (u[p]) s += String.fromCharCode(u[p++]); return s; };
  const chk = (r, what) => { if (r !== 0) throw new Error(`${what}: engine code ${r}: ${cstr(X.GetLastErrorMsg())}`); };
  return { X, out, dv, chk };
}

// Timeline snapshot (Game_Visualiser_ReadTimelineState, 40152 bytes): header + compact entity tables.
function readHeader(e, t, draftBase) {
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true);
  const drafts = [[], []];
  for (let a = 0; a < 2; ++a) for (let b = 0; b < 5; ++b) drafts[a].push(i(draftBase + 12 + a * 20 + b * 4));
  return {
    draftNumRounds: u(draftBase), draftCounts: [u(draftBase + 4), u(draftBase + 8)], drafts,
    round: u(8), turn: u(12), team: u(16), awaitingInput: !!u(20), phase: u(24), outcome: u(28),
    submitted: [Number(e.getBigUint64(t + 32, true)), Number(e.getBigUint64(t + 40, true))],
    inputPosition: u(56), currentChampion: u(60),
    step: {
      phase: u(64), kind: u(68), actor: { kind: u(72), index: u(76) },
      from: { x: i(80), y: i(84) }, to: { x: i(88), y: i(92) }, round: u(96),
      inputPosition: u(100), substep: u(104), slot: u(108), abilityType: u(112), priority: i(116),
    },
  };
}

function readTimeline(e, t) {
  const h = readHeader(e, t, 120);
  const u = (n) => e.getUint32(t + n, true), i = (n) => e.getInt32(t + n, true), f = (n) => e.getFloat32(t + n, true);
  const table = (countOff, dataOff, stride, cap, fn) => {
    const n = u(countOff); if (n > cap) throw new Error('bad snapshot count');
    const r = new Array(n); for (let k = 0; k < n; ++k) r[k] = fn(dataOff + k * stride); return r;
  };
  h.champions = table(172, 196, 252, 16, (n) => {
    const items = []; for (let k = 0; k < ITEM_COUNT; ++k) { const q = u(n + 48 + k * 4); if (q) items.push([k, q]); }
    return {
      index: u(n + 4), team: u(n + 8), type: u(n + 12),
      x: i(n + 16), y: i(n + 20), hp: f(n + 24), maxHp: f(n + 28), alive: !!u(n + 32),
      gold: u(n + 36), gems: u(n + 40), kills: u(n + 44), items,
      cons: [u(n + 216), u(n + 220), u(n + 224), u(n + 228)],
      stunned: !!u(n + 248),
    };
  });
  h.camps = table(176, 4228, 28, 500, (n) => ({ index: u(n + 4), team: u(n + 8), type: u(n + 12), x: i(n + 16), y: i(n + 20), hp: f(n + 24) }));
  h.groups = table(180, 18228, 8, 500, (n) => ({ reward: !!u(n), captureTeam: u(n + 4) }));
  h.wards = table(184, 22228, 8, 128, (n) => ({ team: u(n), disabled: !!u(n + 4) }));
  return h;
}

// Local `cambc run` bundles are zips holding replay.repl26a (plus logs); ladder downloads are the raw replay.
export function unwrapReplay(buf, member = 'replay.repl26a') {
  if (!(buf[0] === 0x50 && buf[1] === 0x4b)) return buf;
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  let off = 0;
  while (off + 30 <= buf.length && dv.getUint32(off, true) === 0x04034b50) {
    const method = dv.getUint16(off + 8, true);
    const csize = dv.getUint32(off + 18, true);
    const nlen = dv.getUint16(off + 26, true), xlen = dv.getUint16(off + 28, true);
    const name = Buffer.from(buf.subarray(off + 30, off + 30 + nlen)).toString();
    const start = off + 30 + nlen + xlen;
    const data = buf.subarray(start, start + csize);
    if (name.endsWith(member)) return method === 8 ? zlib.inflateRawSync(data) : Buffer.from(data);
    off = start + csize;
  }
  throw new Error(`no ${member} inside zip`);
}

export async function decode(buf, opts = {}) {
  buf = unwrapReplay(buf);
  const wasms = findEngineWasms();
  if (!wasms.length) throw new Error('engine wasm not found (run `cambc view` once, or set CAMBC_ENGINE_WASM)');
  let lastErr;
  for (const w of wasms) {
    try { return await decodeWith(w, buf, opts); } catch (err) { lastErr = err; }
  }
  throw lastErr;
}

async function decodeWith(wasmPath, buf, opts) {
  const E = await loadEngine(wasmPath);
  const { X, out, dv, chk } = E;
  const p = X.Engine_Malloc(buf.length);
  new Uint8Array(X.memory.buffer, p, buf.length).set(buf);
  chk(X.Game_FromReplayFileBytes(p, buf.length, out), 'load replay');
  const game = dv().getBigUint64(out, true);
  X.Engine_Free(p);
  if (X.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw new Error('unsupported timeline snapshot layout');
  const snap = X.Engine_Malloc(40152);
  const args = X.Engine_Malloc(128);

  chk(X.Game_GetBitboardMetadata(game, out), 'metadata');
  const width = dv().getInt32(out, true), height = dv().getInt32(out + 4, true);
  chk(X.Game_GetNumChampsPerTeam ? X.Game_GetNumChampsPerTeam(game, out) : 0, 'champs');
  const champsPerTeam = dv().getUint32(out, true);

  chk(X.Game_Visualiser_Timeline_GetMain(game, out), 'main timeline');
  const main = dv().getBigUint64(out, true);
  chk(X.Game_Visualiser_Timeline_Info(game, main, args, args + 8, args + 16), 'timeline info');
  const size = dv().getUint32(args, true);
  chk(X.Game_Visualiser_Timeline_Seek(game, main, 0, 0), 'seek');

  const read = () => { chk(X.Game_Visualiser_ReadTimelineState(game, snap), 'read'); return readTimeline(dv(), snap); };
  const every = opts.every || 1;
  const rounds = [];
  const events = [];
  let prev = read();
  let meta = null;
  let lastRound = -1;
  let guard = 0;
  for (;;) {
    const s = prev;
    if (!meta && s.phase !== 12 && s.champions.length) {
      meta = {
        engine: path.basename(wasmPath), width, height, champsPerTeam,
        drafts: s.drafts.map((d) => d.filter((x) => x >= 0).map((x) => DRAFT[x] ?? x)),
        bodies: s.champions.map((c) => ({ index: c.index, team: c.team, type: CHAMP[c.type] ?? c.type })),
        camps: s.camps.map((c) => ({ index: c.index, type: CAMP[c.type] ?? c.type, x: c.x, y: c.y, hp: c.hp })),
      };
    }
    if (s.outcome || (s.awaitingInput && s.inputPosition >= size)) break;
    X.Game_Visualiser_Timeline_ReplayNext(game, 1);
    const n = read();
    if (n.inputPosition === s.inputPosition && n.step.substep === s.step.substep) throw new Error('timeline made no progress');
    if (++guard > 5e6) throw new Error('runaway replay');
    // Events from the step that produced n
    const st = n.step;
    if (n.phase !== 12 && st.kind !== 0 && st.kind !== 3 && st.kind !== 7) {
      const ev = { r: st.round, k: STEP[st.kind] || st.kind };
      if (st.actor.kind === 1) {
        const c = n.champions.find((q) => q.index === st.actor.index);
        ev.who = st.actor.index; if (c) { ev.team = c.team; ev.champ = CHAMP[c.type]; }
      } else if (st.actor.kind === 2) { ev.camp = st.actor.index; }
      else ev.actorKind = st.actor.kind;
      if (st.from.x >= 0) ev.from = [st.from.x, st.from.y];
      if (st.to.x >= 0) ev.to = [st.to.x, st.to.y];
      if (st.kind === 6) { ev.slot = st.slot; ev.ability = st.abilityType; }
      if (st.kind === 9) ev.priority = st.priority;
      if ((st.kind !== 8 || opts.endturns) && (st.kind !== 26 || opts.rollovers)) events.push(ev); // 26: a turn that ran out of fuel continues next round
    }
    // Derived: deaths and captures by diffing champion / group state
    const pm = new Map(s.champions.map((c) => [c.index, c]));
    for (const c of n.champions) {
      const o = pm.get(c.index);
      if (o && o.alive && !c.alive) {
        events.push({ r: n.step.round, k: 'Death', who: c.index, team: c.team, champ: CHAMP[c.type], at: [o.x, o.y], bag: o.gems,
          by: st.actor.kind === 1 ? st.actor.index : (st.actor.kind === 2 ? 'camp' : st.actor.kind), step: STEP[st.kind] });
      }
      if (o && c.gems > o.gems && st.kind === 2) events.push({ r: n.step.round, k: 'CaptureGems', who: c.index, team: c.team, champ: CHAMP[c.type], gems: c.gems - o.gems, gold: c.gold - o.gold, at: [c.x, c.y] });
      if (o && c.gems < o.gems && c.alive && st.kind === 18) events.push({ r: n.step.round, k: 'Banked', who: c.index, team: c.team, champ: CHAMP[c.type], gems: o.gems - c.gems, at: [c.x, c.y] });
    }
    if (n.step.round !== lastRound && n.phase !== 12) {
      // state at the first step of a new round = end of the previous round
      if (lastRound >= 0 && (lastRound % every === 0)) rounds.push(compact(s, lastRound));
      lastRound = n.step.round;
    }
    prev = n;
  }
  rounds.push(compact(prev, prev.step.round));
  meta = meta || {};
  meta.outcome = prev.outcome; // 1 = team A (0) won, 2 = team B (1) won (engine encoding)
  meta.finalRound = prev.step.round;
  meta.submitted = prev.submitted;
  meta.size = size;
  return { meta, rounds, events };
}

function compact(s, r) {
  return {
    r, sub: s.submitted,
    ch: s.champions.map((c) => [c.index, c.team, c.type, c.x, c.y, Math.round(c.hp), Math.round(c.maxHp), c.alive ? 1 : 0, c.gems, c.gold, c.kills, c.items, c.stunned ? 1 : 0, c.cons]),
    gr: s.groups.map((g) => (g.reward ? 1 : 0)),
    campHp: s.camps.map((c) => Math.round(c.hp)),
    wards: s.wards.filter((w) => !w.disabled).map((w) => w.team),
  };
}

if (false) {
  const argv = process.argv.slice(2);
  const file = argv.find((a) => !a.startsWith('--') && !/^\d+$/.test(a));
  if (!file) { console.error('usage: decode.mjs replay.repl26a [--out file.json] [--every N]'); process.exit(2); }
  const oi = argv.indexOf('--out');
  const ei = argv.indexOf('--every');
  const res = await decode(fs.readFileSync(file), { every: ei >= 0 ? +argv[ei + 1] : 1 });
  const text = JSON.stringify(res);
  if (oi >= 0) fs.writeFileSync(argv[oi + 1], text); else process.stdout.write(text + '\n');
}
