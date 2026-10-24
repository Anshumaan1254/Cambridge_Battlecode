#!/usr/bin/env python3
"""RL trainer for the HouseOfCoders bot (CAMBC 2026a): finds the best parameters, strategy switches and draft weights.

WHAT IT DOES
  Black-box reinforcement learning (evolution strategies over the bot's policy parameters, Salimans et al. 2017) with
  the real engine as the simulator. The policy is bots/<base>/src/params.h (the bot's scoring rules, fight / flee
  thresholds, farming, banking, build, stance learner, strategy switches, draft priors); a submitted bot can neither
  learn between matches nor afford a neural network in 100k fuel per turn, so its parameter vector is what we train.

  Lessons of the 3,600 ladder games this session built in (tools/rl/knowledge.json):
    * Local games against ONE copy of ourselves misled us three times. Candidates therefore play a LEAGUE of different
      styles (the live bot, a "brave" bot that farms through enemies like the top teams, the previous live bot, the bb4
      modules, six strategy personas, and every accepted champion: hall of fame).
    * Games are deterministic: every candidate of a generation plays the same (map, side, opponent) cases as the
      incumbent (common random numbers), and scores are PAIRED differences to the incumbent on those cases.
    * Maps are drawn by ladder frequency x how badly we do there vs the top 10.
    * Reward = win + banked-gem margin + round-300 economy + first kill - deaths + fast wins - faults / fuel-outs (the
      early-economy terms are the ladder's strongest predictors of the result).
    * Ladder A/B evidence is the prior: e.g. the archetype draft (-8 points on the ladder) starts at 5% probability.
  Search: each generation perturbs 1-2 parameter BLOCKS (fight, farm, economy, team, switches, draft) chosen by a
  bandit, samples antithetic candidates, races them with successive halving, and validates the winner on FRESH cases
  before accepting it (paired one-sided t-test), so accepted changes are not selection noise. A final championship
  ranks the start point, the final incumbent and the best runners-up on new cases.

OUTPUT (rl_results/<run>/ and the archive rl_results_<run>.tar.gz in the project root)
  best_params.json          the winning parameter values (every gene) and the changes vs the start point
  learned_distribution.json the learned search distribution (gene means, step sizes, switch probabilities) = "weights"
  report.md                 summary: what changed, league results before / after, history
  history.jsonl, games.jsonl, state.json (resume), train.log

USAGE (Linux; run from anywhere inside the cambc project)
  pip install cambc==3.0.5          # the project's SDK version (cambc.toml)
  python3 tools/rl/train_rl.py --hours 3.5                 # full run (auto workers)
  python3 tools/rl/train_rl.py --smoke                     # ~20-30 minute end-to-end check
  python3 tools/rl/train_rl.py --resume rl_results/<run> --hours 2
Options: --workers N (parallel games), --build-jobs N, --base bb4, --seed S, --pop N, --blocks-per-gen N, --keep-bots.
Only the Python standard library is needed (Python 3.8+).
"""
import argparse
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
KNOWLEDGE = os.path.join(ROOT, "tools", "rl", "knowledge.json")
STOP = {"gens": False, "now": False}
LOG = {"fh": None}


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if LOG["fh"]:
        LOG["fh"].write(line + "\n")
        LOG["fh"].flush()


def on_signal(signum, frame):
    if STOP["gens"]:
        STOP["now"] = True
        log("second interrupt: exiting now (state was saved after the last batch; --resume continues)")
        sys.exit(130)
    STOP["gens"] = True
    log("interrupt: no new generation work; the championship and the results still run (Ctrl-C again to exit at once)")


# ---------------------------------------------------------------------------------------------------- params.h

PARAM_RE = r"^(\s*(?:static\s+)?(?:constexpr\s+)?(int|float|long long|bool|double)\s+{name}\s*=\s*)([^;]*);"


def read_param_types(src):
    out = {}
    for m in re.finditer(r"^\s*(?:static\s+)?(?:constexpr\s+)?(int|float|long long|bool|double)\s+(\w+)\s*=\s*([^;]+);", src, re.M):
        out[m.group(2)] = (m.group(1), m.group(3).strip())
    return out


def fmt_value(ptype, v):
    if ptype == "float":
        return f"{float(v):.5f}f"
    if ptype == "double":
        return f"{float(v):.6f}"
    if ptype == "bool":
        return "true" if v else "false"
    return str(int(round(float(v))))


def patch_params(src, overrides, types):
    for name, v in overrides.items():
        if name not in types:
            raise KeyError(f"parameter {name} not found in params.h")
        pat = re.compile(PARAM_RE.format(name=re.escape(name)), re.M)
        val = fmt_value(types[name][0], v)
        src, n = pat.subn(lambda m: m.group(1) + val + ";", src, count=1)
        if n != 1:
            raise KeyError(f"parameter {name}: could not patch")
    return src


# ---------------------------------------------------------------------------------------------------- search space

class Space:
    def __init__(self, knowledge, types):
        self.genes = knowledge["genes"]
        self.by = {g["name"]: g for g in self.genes}
        missing = [g["name"] for g in self.genes if g["type"] != "bit" and g["name"] not in types]
        if missing:
            raise SystemExit("knowledge.json genes missing from params.h: " + ", ".join(missing))
        self.blocks = sorted({g["block"] for g in self.genes})

    def init_genome(self):
        return {g["name"]: g["init"] for g in self.genes}

    def init_dist(self):
        d = {}
        for g in self.genes:
            if g["type"] in ("float", "int"):
                d[g["name"]] = {"m": self.norm(g, g["init"]), "s": g.get("sigma", 0.15)}
            elif g["type"] == "bit":
                d[g["name"]] = {"p": g["p"]}
            else:
                d[g["name"]] = {"probs": list(g["probs"])}
        return d

    @staticmethod
    def norm(g, x):
        return (float(x) - g["lo"]) / max(1e-9, g["hi"] - g["lo"])

    @staticmethod
    def denorm(g, u):
        u = min(1.0, max(0.0, u))
        x = g["lo"] + u * (g["hi"] - g["lo"])
        return int(round(x)) if g["type"] == "int" else round(x, 5)

    def to_params(self, genome, extra=None):
        """genome -> params.h overrides: switch bits are summed into ab_base."""
        p = {}
        ab = 0
        for g in self.genes:
            v = genome[g["name"]]
            if g["type"] == "bit":
                ab |= g["bit"] if v else 0
            else:
                p[g["name"]] = v
        p["ab_base"] = ab
        if extra:
            p.update(extra)
        return p

    def key(self, genome, extra=None):
        blob = json.dumps({"g": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in sorted(genome.items())},
                           "x": extra or {}}, sort_keys=True)
        return hashlib.sha1(blob.encode()).hexdigest()[:10]

    def sample(self, dist, center, blocks, rng, eps=None, max_flips=3):
        """One candidate: genes of the chosen blocks drawn from the search distribution, the rest from `center`; at most
        max_flips switch / category genes differ from `center` (extra flips are reverted at random), so wins stay attributable."""
        g = dict(center)
        used = {}
        for gene in self.genes:
            if gene["block"] not in blocks:
                continue
            n = gene["name"]
            if gene["type"] in ("float", "int"):
                e = eps[n] if eps and n in eps else rng.gauss(0.0, 1.0)
                used[n] = e
                g[n] = self.denorm(gene, dist[n]["m"] + dist[n]["s"] * e)
            elif gene["type"] == "bit":
                g[n] = 1 if rng.random() < dist[n]["p"] else 0
            else:
                probs = dist[n]["probs"]
                r, acc, pick = rng.random(), 0.0, gene["values"][-1]
                for v, pr in zip(gene["values"], probs):
                    acc += pr
                    if r < acc:
                        pick = v
                        break
                g[n] = pick
        flips = [x["name"] for x in self.genes if x["type"] in ("bit", "cat") and g[x["name"]] != center[x["name"]]]
        if max_flips is not None and len(flips) > max_flips:
            rng.shuffle(flips)
            for n in flips[max_flips:]:
                g[n] = center[n]
        return g, used


# ---------------------------------------------------------------------------------------------------- statistics -> reward

def value_at(runs, r):
    t = 0
    last = 0.0
    for run in runs:
        try:
            v = float(run.get("value", 0))
        except (TypeError, ValueError):
            v = 0.0
        d = int(run.get("duration", 0))
        if r < t + d:
            return v
        t += d
        last = v
    return last


def team_numbers(d, team):
    champs = [c for c in d.get("champions", []) if c.get("team") == team]
    gems = 0
    for t in d.get("teams", []):
        if t.get("team") == team:
            gems = float(t.get("submittedGems", 0))
    deaths = sum(float(c["metrics"].get("deaths", 0)) for c in champs)
    kills = sum(float(c["metrics"].get("kills", 0)) for c in champs)
    tl = [t for t in d.get("championTimelines", []) if (t.get("owner") or {}).get("team") == team]

    def at(metric, r):
        return sum(value_at(t["runs"], r) for t in tl if t.get("metric") == metric)

    first_kill = None
    for t in tl:
        if t.get("metric") != "kills":
            continue
        s = 0
        for run in t["runs"]:
            try:
                v = float(run.get("value", 0))
            except (TypeError, ValueError):
                v = 0.0
            if v > 0:
                first_kill = s if first_kill is None else min(first_kill, s)
                break
            s += int(run.get("duration", 0))
    fuel = 0
    for e in d.get("events", []):
        if e.get("kind") == "fuelExhausted" and (e.get("owner") or {}).get("team") == team:
            fuel += sum(1 for x in e.get("entries", []) if ((x.get("timestamp") or {}).get("round", 0)) > 5)
    faults = ((d.get("diagnostics") or {}).get("botFaults") or {}).get(team, 0) or 0
    return {"gems": gems, "deaths": deaths, "kills": kills, "collected300": at("collectedGems", 300), "gold300": at("earnedGold", 300),
            "deaths300": at("deaths", 300), "first_kill": first_kill, "fuel": fuel, "faults": float(faults)}


def game_reward(d, us, W):
    them = "teamB" if us == "teamA" else "teamA"
    a, b = team_numbers(d, us), team_numbers(d, them)
    outcome = (d.get("match") or {}).get("outcome")
    rounds = int((d.get("match") or {}).get("roundsCompleted", 2000) or 2000)
    win = 1 if outcome == us else -1 if outcome == them else (1 if a["gems"] > b["gems"] else -1 if a["gems"] < b["gems"] else 0)
    ea = a["collected300"] + W["econ_gold_weight"] * a["gold300"]
    eb = b["collected300"] + W["econ_gold_weight"] * b["gold300"]
    fk = 0
    if a["first_kill"] is not None and (b["first_kill"] is None or a["first_kill"] < b["first_kill"]):
        fk = 1
    elif b["first_kill"] is not None and (a["first_kill"] is None or b["first_kill"] < a["first_kill"]):
        fk = -1
    r = (W["win"] * win
         + W["gem_diff"] * max(-1.0, min(1.0, (a["gems"] - b["gems"]) / W["gem_diff_scale"]))
         + W["econ300"] * math.tanh((ea - eb) / W["econ300_scale"])
         + W["first_kill"] * fk
         - W["deaths"] * (a["deaths"] - b["deaths"])
         + (W["fast_win"] * (2000 - rounds) / 2000.0 if win == 1 else 0.0)
         - W["fault"] * min(1.0, a["faults"])
         - W["fuel_out"] * min(20, a["fuel"]))
    return {"r": round(r, 4), "win": win, "gems": a["gems"], "gems_opp": b["gems"], "deaths": a["deaths"], "deaths_opp": b["deaths"],
            "econ300": round(ea, 1), "econ300_opp": round(eb, 1), "first_kill": fk, "rounds": rounds, "fuel": a["fuel"], "faults": a["faults"]}


# ---------------------------------------------------------------------------------------------------- the trainer

class Trainer:
    def __init__(self, a):
        self.a = a
        self.k = json.load(open(KNOWLEDGE, encoding="utf-8"))
        self.base = a.base or self.k.get("base_bot", "bb4")
        self.base_dir = os.path.join(ROOT, "bots", self.base)
        hp = os.path.join(self.base_dir, "src", "params.h")
        if not os.path.exists(hp):
            raise SystemExit(f"base bot not found: {hp}")
        self.params_src = open(hp, encoding="utf-8").read()
        self.types = read_param_types(self.params_src)
        self.space = Space(self.k, self.types)
        self.W = self.k["reward"]
        self.maps = {m: v["weight"] for m, v in self.k["maps"].items() if os.path.exists(os.path.join(ROOT, "maps", m + ".map26a"))}
        if not self.maps:
            raise SystemExit("no maps from knowledge.json found under maps/")
        self.cambc = shutil.which("cambc") or shutil.which("cambc.exe")
        if not self.cambc:
            raise SystemExit("cambc not found on PATH: pip install cambc==3.0.5")
        self.cpu = os.cpu_count() or 4
        self.workers = a.workers or self.auto_workers()
        self.build_jobs = a.build_jobs or max(2, min(8, self.cpu // 3))
        self.state = None
        self.built = {}  # bot name -> True / False
        self.batch_no = 0
        self.sec_per_game = None
        self.sec_per_wave = None

    # ----- hardware
    def auto_workers(self):
        mem_gb = None
        try:
            for l in open("/proc/meminfo"):
                if l.startswith("MemAvailable:"):
                    mem_gb = int(l.split()[1]) / 1024 / 1024
        except OSError:
            pass
        w = max(1, self.cpu - 2)
        if mem_gb:
            w = min(w, max(1, int(mem_gb / 0.7)))
        return min(w, 24)

    # ----- persistence
    def save(self):
        st = self.state
        st["rng"] = self.rng_state()
        tmp = os.path.join(self.out, "state.json.tmp")
        json.dump(st, open(tmp, "w", encoding="utf-8"))
        os.replace(tmp, os.path.join(self.out, "state.json"))

    def rng_state(self):
        s = self.rng.getstate()
        return [s[0], list(s[1]), s[2]]

    def set_rng(self, s):
        self.rng.setstate((s[0], tuple(s[1]), s[2]))

    # ----- bots
    def bot_name(self, key):
        return f"_rl_{key}"

    def make_bot(self, name, overrides):
        d = os.path.join(ROOT, "bots", name)
        src = os.path.join(d, "src")
        want = patch_params(self.params_src, overrides, self.types)
        hp = os.path.join(src, "params.h")
        if os.path.exists(hp) and open(hp, encoding="utf-8").read() == want:
            return name  # same parameters: keep the directory (and its build cache)
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        shutil.copytree(os.path.join(self.base_dir, "src"), src)
        for f in os.listdir(self.base_dir):
            p = os.path.join(self.base_dir, f)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(d, f))
        open(hp, "w", encoding="utf-8").write(want)
        self.built.pop(name, None)
        return name

    def build(self, names):
        todo = [n for n in dict.fromkeys(names) if not self.built.get(n)]
        if not todo:
            return
        t0 = time.time()
        os.makedirs(os.path.join(self.out, "build_logs"), exist_ok=True)

        def one(n):
            try:
                r = subprocess.run([self.cambc, "build", n, "--release"], cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=3600)
            except subprocess.TimeoutExpired as e:
                r = subprocess.CompletedProcess(e.cmd, 1, str(e.stdout or ""), "build timed out")
            wasm = os.path.join(ROOT, "bots", n, ".cambc", "build-release", "bot-injected.wasm")
            ok = r.returncode == 0 and (os.path.exists(wasm) or "built" in (r.stdout + r.stderr))
            if not ok:
                open(os.path.join(self.out, "build_logs", n + ".log"), "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
            return n, ok

        with ThreadPoolExecutor(self.build_jobs) as ex:
            for n, ok in ex.map(one, todo):
                self.built[n] = ok
        waves = math.ceil(len(todo) / self.build_jobs)
        wave = (time.time() - t0) / max(1, waves)
        self.sec_per_wave = wave if self.sec_per_wave is None else 0.6 * self.sec_per_wave + 0.4 * wave
        bad = [n for n in todo if not self.built[n]]
        log(f"built {len(todo) - len(bad)}/{len(todo)} bots in {time.time() - t0:.0f}s" + (f" (FAILED: {', '.join(bad)}; see build_logs/)" if bad else ""))

    def genome_bot(self, genome, extra=None):
        key = self.space.key(genome, extra)
        name = self.bot_name(key)
        if not self.built.get(name):
            self.make_bot(name, self.space.to_params(genome, dict(self.k.get("base_overrides", {}), **(extra or {}))))
        return name

    # ----- league
    def setup_league(self):
        st = self.state
        if st.get("league"):
            return
        league = []
        base = st["start"]
        for L in self.k["league"][: (3 if self.a.smoke else None)]:
            g = dict(base)
            g.update(L.get("genes", {}))
            name = self.genome_bot(g, L.get("params"))
            league.append({"name": L["name"], "bot": name, "weight": L["weight"], "genome": g, "params": L.get("params", {})})
        st["league"] = league
        st["hof"] = []

    def opponents(self):
        st = self.state
        opp = [(L["name"], L["bot"], L["weight"]) for L in st["league"]]
        if st["hof"]:
            w = self.k.get("hall_of_fame_weight", 0.06) / len(st["hof"])
            opp += [(h["name"], h["bot"], w) for h in st["hof"]]
        return opp

    # ----- cases
    def sample_cases(self, n, exclude):
        maps = list(self.maps)
        mw = [self.maps[m] for m in maps]
        opp = self.opponents()
        ow = [o[2] for o in opp]
        cases, tries = [], 0
        ex = set(map(tuple, exclude))
        while len(cases) < n and tries < n * 200:
            tries += 1
            m = self.rng.choices(maps, mw)[0]
            s = self.rng.choice("AB")
            o = self.rng.choices(opp, ow)[0]
            c = (m, s, o[0])
            if c in ex:
                continue
            ex.add(c)
            cases.append(c)
        return cases

    def opp_bot(self, oname):
        for o in self.opponents():
            if o[0] == oname:
                return o[1]
        raise KeyError(oname)

    # ----- games
    def run_games(self, games):
        """games: list of (bot, case). Returns {(bot, case): result}; results are cached in state['cache']."""
        cache = self.state["cache"]
        todo = []
        for bot, case in games:
            k = f"{bot}|{case[0]}|{case[1]}|{case[2]}"
            if k not in cache and (bot, case) not in todo:
                todo.append((bot, case))
        if todo:
            self.build([b for b, _ in todo] + [self.opp_bot(c[2]) for _, c in todo])
            for attempt in range(2):
                todo = [(b, c) for b, c in todo if f"{b}|{c[0]}|{c[1]}|{c[2]}" not in cache and self.built.get(b) and self.built.get(self.opp_bot(c[2]))]
                if not todo or STOP["now"]:
                    break
                self.play(todo)
        out = {}
        for bot, case in games:
            out[(bot, case)] = cache.get(f"{bot}|{case[0]}|{case[1]}|{case[2]}")
        return out

    def play(self, todo):
        self.batch_no += 1
        bdir = os.path.join(self.out, "tmp", f"b{self.batch_no}")
        os.makedirs(bdir, exist_ok=True)
        rows = []
        for i, (bot, (mp, side, oname)) in enumerate(todo):
            ob = self.opp_bot(oname)
            a_, b_ = (bot, ob) if side == "A" else (ob, bot)
            stem = os.path.join(bdir, f"g{i}").replace("\\", "/")
            rows.append(f'bots/{a_} bots/{b_} "maps/{mp}.map26a" "{stem}.repl26a" --statistics "{stem}.json" --json')
        man = os.path.join(ROOT, f".rl_manifest_{os.getpid()}_{self.batch_no}.txt")
        open(man, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        t0 = time.time()
        logf = open(os.path.join(bdir, "run.log"), "w", encoding="utf-8")
        cmd = [self.cambc, "run-batch", os.path.basename(man), "--jobs", str(self.workers), "--release", "--color", "never",
               "--timeout", str(self.a.game_timeout)]
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT)
        last = 0
        while p.poll() is None:
            time.sleep(5)
            if time.time() - last > 60:
                last = time.time()
                done = len([f for f in os.listdir(bdir) if f.endswith(".json")])
                log(f"  batch {self.batch_no}: {done}/{len(todo)} games, {time.time() - t0:.0f}s")
        logf.close()
        try:
            os.remove(man)
        except OSError:
            pass
        wall = time.time() - t0
        ok = 0
        cache = self.state["cache"]
        gl = open(os.path.join(self.out, "games.jsonl"), "a", encoding="utf-8")
        for i, (bot, (mp, side, oname)) in enumerate(todo):
            stem = os.path.join(bdir, f"g{i}")
            try:
                d = json.load(open(stem + ".json", encoding="utf-8"))
                res = game_reward(d, "teamA" if side == "A" else "teamB", self.W)
            except (OSError, ValueError, KeyError) as e:
                res = None
            if res is not None:
                ok += 1
                cache[f"{bot}|{mp}|{side}|{oname}"] = res
                gl.write(json.dumps({"bot": bot, "map": mp, "side": side, "opp": oname, **res}) + "\n")
            for ext in (".json", ".repl26a"):
                try:
                    os.remove(stem + ext)
                except OSError:
                    pass
        gl.close()
        if ok:
            spg = wall / max(1, len(todo))
            self.sec_per_game = spg if self.sec_per_game is None else 0.7 * self.sec_per_game + 0.3 * spg
        log(f"  batch {self.batch_no}: {ok}/{len(todo)} games ok in {wall:.0f}s ({wall / max(1, len(todo)):.1f}s per game with {self.workers} workers)")
        if ok < len(todo):
            log(f"  {len(todo) - ok} games failed (see {bdir}/run.log)")
        else:
            shutil.rmtree(bdir, ignore_errors=True)
        self.save()

    # ----- scoring
    def paired(self, bot, ref, cases):
        res = self.run_games([(bot, c) for c in cases] + [(ref, c) for c in cases])
        diffs = []
        for c in cases:
            x, y = res.get((bot, c)), res.get((ref, c))
            if x is not None and y is not None:
                diffs.append(x["r"] - y["r"])
        return diffs

    @staticmethod
    def tstat(d):
        if len(d) < 2:
            return 0.0
        m = sum(d) / len(d)
        v = sum((x - m) ** 2 for x in d) / (len(d) - 1)
        if v <= 1e-12:
            return 99.0 if m > 0 else (-99.0 if m < 0 else 0.0)
        return m / math.sqrt(v / len(d))

    # ----- block bandit
    def choose_blocks(self):
        st = self.state
        k = max(1, min(self.a.blocks_per_gen, len(self.space.blocks)))
        stats = st["block_stats"]
        scores = []
        for b in self.space.blocks:
            s = stats.setdefault(b, {"tries": 0, "wins": 0.0})
            scores.append((self.rng.betavariate(1 + s["wins"], 1 + s["tries"] - s["wins"]), b))
        scores.sort(reverse=True)
        return [b for _, b in scores[:k]]

    # ----- one generation
    def generation(self):
        st = self.state
        a = self.a
        gen = st["gen"] + 1
        blocks = self.choose_blocks()
        inc = st["incumbent"]
        inc_bot = self.genome_bot(inc)
        log(f"=== generation {gen}: blocks {blocks}; incumbent {inc_bot}")
        cands, seen = [], {self.space.key(inc)}
        tries = 0
        while len(cands) < a.pop and tries < a.pop * 20:
            tries += 1
            g1, eps = self.space.sample(st["dist"], inc, blocks, self.rng, max_flips=a.max_flips)
            pair = [g1]
            if eps and len(cands) + 1 < a.pop:
                g2, _ = self.space.sample(st["dist"], inc, blocks, self.rng, eps={k_: -v for k_, v in eps.items()}, max_flips=a.max_flips)
                pair.append(g2)
            for g in pair:
                kk = self.space.key(g)
                if kk not in seen:
                    seen.add(kk)
                    cands.append(g)
        bots = [self.genome_bot(g) for g in cands]
        self.build([inc_bot] + bots)
        alive = [(g, b) for g, b in zip(cands, bots) if self.built.get(b)]
        if not alive:
            log("no candidate built; skipping generation")
            st["gen"] = gen
            return
        used = []
        scores = {b: [] for _, b in alive}
        rungs = [(len(alive), a.rung1), (a.keep2, a.rung2), (a.keep3, a.rung3)]
        pool = alive
        for i, (keep, n) in enumerate(rungs):
            if STOP["gens"] or n <= 0 or not pool:
                break
            pool = pool[:keep]
            cases = self.sample_cases(n, used)
            used += cases
            for g, b in pool:
                scores[b] += self.paired(b, inc_bot, cases)
            pool.sort(key=lambda gb: -(sum(scores[gb[1]]) / max(1, len(scores[gb[1]]))))
            log(f"  rung {i + 1}: " + ", ".join(f"{gb[1][-6:]} {sum(scores[gb[1]]) / max(1, len(scores[gb[1]])):+.3f}(n{len(scores[gb[1]])})" for gb in pool))
        best_g, best_b = pool[0]
        sel_mean = sum(scores[best_b]) / max(1, len(scores[best_b]))
        # validation on fresh cases (no selection bias)
        val = []
        if not STOP["gens"] and a.valid > 0 and sel_mean > 0:
            vcases = self.sample_cases(a.valid, used)
            used += vcases
            val = self.paired(best_b, inc_bot, vcases)
        vmean = sum(val) / len(val) if val else 0.0
        t = self.tstat(val)
        accepted = bool(val) and vmean > 0 and t >= a.t_accept
        log(f"  best {best_b}: selection {sel_mean:+.3f} (n{len(scores[best_b])}), validation {vmean:+.3f} t={t:.2f} (n{len(val)}) -> "
            + ("ACCEPTED" if accepted else "kept incumbent"))
        # distribution update on the chosen blocks (rank-weighted mean of the better half of the candidates)
        ranked = sorted(alive, key=lambda gb: -(sum(scores[gb[1]]) / max(1, len(scores[gb[1]]))))
        mu = max(1, len(ranked) // 2)
        wts = [math.log(mu + 0.5) - math.log(i + 1) for i in range(mu)]
        sw = sum(wts)
        wts = [w / sw for w in wts]
        for gene in self.space.genes:
            if gene["block"] not in blocks:
                continue
            n = gene["name"]
            dd = st["dist"][n]
            if gene["type"] in ("float", "int"):
                target = sum(w * self.space.norm(gene, ranked[i][0][n]) for i, w in enumerate(wts))
                if accepted:
                    target = self.space.norm(gene, best_g[n])
                dd["m"] = (1 - a.lr) * dd["m"] + a.lr * target if not accepted else target
                dd["s"] = max(a.sigma_min, min(0.35, dd["s"] * (1.0 if accepted else a.sigma_decay)))
            elif gene["type"] == "bit":
                f = sum(w * ranked[i][0][n] for i, w in enumerate(wts))
                if accepted:
                    f = best_g[n]
                dd["p"] = min(0.95, max(0.05, (1 - a.pbil) * dd["p"] + a.pbil * f))
            else:
                vals = gene["values"]
                f = [sum(w for i, w in enumerate(wts) if ranked[i][0][n] == v) for v in vals]
                if accepted:
                    f = [1.0 if v == best_g[n] else 0.0 for v in vals]
                pr = [(1 - a.pbil) * p + a.pbil * x for p, x in zip(dd["probs"], f)]
                pr = [min(0.95, max(0.03, p)) for p in pr]
                s = sum(pr)
                dd["probs"] = [p / s for p in pr]
        for b in blocks:
            bs = st["block_stats"].setdefault(b, {"tries": 0, "wins": 0.0})
            bs["tries"] += 1
            bs["wins"] += 1.0 if accepted else (0.3 if sel_mean > 0 else 0.0)
        rec = {"gen": gen, "blocks": blocks, "incumbent": inc_bot, "best": best_b, "selection": round(sel_mean, 4), "n_sel": len(scores[best_b]),
               "validation": round(vmean, 4), "t": round(t, 3), "n_val": len(val), "accepted": accepted,
               "changes": {k_: [inc[k_], best_g[k_]] for k_ in best_g if best_g[k_] != inc[k_]},
               "candidates": [{"bot": b, "score": round(sum(scores[b]) / max(1, len(scores[b])), 4), "n": len(scores[b])} for _, b in ranked],
               "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        open(os.path.join(self.out, "history.jsonl"), "a", encoding="utf-8").write(json.dumps(rec) + "\n")
        if accepted:
            st["hof"].append({"name": f"hof{gen}", "bot": inc_bot, "genome": inc})
            st["incumbent"] = best_g
            st["accepted"].append({"gen": gen, "bot": best_b, "validation": round(vmean, 4), "t": round(t, 3)})
        elif val and vmean > 0:
            st["runners"].append({"gen": gen, "bot": best_b, "genome": best_g, "validation": round(vmean, 4), "t": round(t, 3)})
        st["gen"] = gen
        self.save()
        if not self.a.keep_bots:
            self.prune()

    def prune(self):
        st = self.state
        keep = {L["bot"] for L in st["league"]} | {h["bot"] for h in st["hof"]} | {self.genome_bot(st["incumbent"]), self.genome_bot(st["start"])}
        keep |= {r["bot"] for r in st["runners"]}
        bd = os.path.join(ROOT, "bots")
        for n in os.listdir(bd):
            if n.startswith("_rl_") and n not in keep:
                shutil.rmtree(os.path.join(bd, n), ignore_errors=True)
                self.built.pop(n, None)

    # ----- final championship
    def championship(self):
        st = self.state
        fin = [("start", st["start"]), ("final", st["incumbent"])]
        for r in sorted(st["runners"], key=lambda r: -r["validation"])[:2]:
            fin.append((f"runner_g{r['gen']}", r["genome"]))
        uniq, seen = [], set()
        for nm, g in fin:
            k_ = self.space.key(g)
            if k_ not in seen:
                seen.add(k_)
                uniq.append((nm, g, self.genome_bot(g)))
        cases = self.sample_cases(self.a.final, [])
        log(f"=== championship: {', '.join(n for n, _, _ in uniq)} on {len(cases)} fresh cases")
        res = self.run_games([(b, c) for _, _, b in uniq for c in cases])
        table = []
        for nm, g, b in uniq:
            rs = [res.get((b, c)) for c in cases]
            rs = [x for x in rs if x]
            if not rs:
                continue
            per_opp = {}
            for c in cases:
                x = res.get((b, c))
                if x:
                    po = per_opp.setdefault(c[2], [0, 0])
                    po[0] += x["win"] == 1
                    po[1] += 1
            table.append({"name": nm, "bot": b, "genome": g, "reward": round(sum(x["r"] for x in rs) / len(rs), 4),
                          "winrate": round(sum(x["win"] == 1 for x in rs) / len(rs), 4), "n": len(rs),
                          "gems": round(sum(x["gems"] for x in rs) / len(rs), 1), "gems_opp": round(sum(x["gems_opp"] for x in rs) / len(rs), 1),
                          "deaths": round(sum(x["deaths"] for x in rs) / len(rs), 2), "deaths_opp": round(sum(x["deaths_opp"] for x in rs) / len(rs), 2),
                          "per_opponent": {o: f"{w}/{n}" for o, (w, n) in sorted(per_opp.items())}})
        # paired comparison with the start point on the same cases
        sb = next((t["bot"] for t in table if t["name"] == "start"), None)
        for t in table:
            if sb and t["bot"] != sb:
                d = [res[(t["bot"], c)]["r"] - res[(sb, c)]["r"] for c in cases if res.get((t["bot"], c)) and res.get((sb, c))]
                t["paired_vs_start"] = round(sum(d) / max(1, len(d)), 4)
                t["paired_t"] = round(self.tstat(d), 2)
        table.sort(key=lambda t: -t["reward"])
        st["championship"] = table
        self.save()
        return table

    # ----- outputs
    def write_results(self):
        st = self.state
        table = st.get("championship") or []
        best = None
        if table:
            # the best by championship reward; the start point only if nothing beat it
            best = table[0]
        bg = best["genome"] if best else st["incumbent"]
        start = st["start"]
        params = self.space.to_params(bg)
        changed = {}
        for g in self.space.genes:
            if bg[g["name"]] != start[g["name"]]:
                changed[g["name"]] = {"from": start[g["name"]], "to": bg[g["name"]], "block": g["block"], "note": g.get("note", "")}
        out = {"base_bot": self.base, "chosen": best["name"] if best else "incumbent", "genome": bg, "params_h_overrides": params,
               "changed_vs_start": changed, "championship": [{k_: v for k_, v in t.items() if k_ != "genome"} for t in table],
               "accepted": st["accepted"], "generations": st["gen"], "games": len(st["cache"]),
               "machine": {"platform": platform.platform(), "cpus": self.cpu, "workers": self.workers}}
        json.dump(out, open(os.path.join(self.out, "best_params.json"), "w", encoding="utf-8"), indent=1)
        dist = {}
        for g in self.space.genes:
            d = st["dist"][g["name"]]
            if g["type"] in ("float", "int"):
                dist[g["name"]] = {"block": g["block"], "mean": self.space.denorm(g, d["m"]), "sigma_norm": round(d["s"], 4),
                                   "lo": g["lo"], "hi": g["hi"], "start": start[g["name"]]}
            elif g["type"] == "bit":
                dist[g["name"]] = {"block": g["block"], "p_on": round(d["p"], 4), "start": start[g["name"]]}
            else:
                dist[g["name"]] = {"block": g["block"], "probs": {str(v): round(p, 4) for v, p in zip(g["values"], d["probs"])}, "start": start[g["name"]]}
        json.dump({"genes": dist, "block_stats": st["block_stats"]}, open(os.path.join(self.out, "learned_distribution.json"), "w", encoding="utf-8"), indent=1)
        L = []
        L.append(f"# RL training report ({self.base})\n")
        L.append(f"- run: {os.path.basename(self.out)}, generations {st['gen']}, games {len(st['cache'])}, accepted changes {len(st['accepted'])}")
        L.append(f"- machine: {platform.platform()}, {self.cpu} CPUs, {self.workers} parallel games, {self.sec_per_game or 0:.1f}s wall per game")
        L.append(f"- league: {', '.join(x['name'] for x in st['league'])} + hall of fame {len(st['hof'])}\n")
        L.append("## Championship (fresh cases, same for every finalist)\n")
        L.append("| finalist | reward | win rate | gems (us-them) | deaths (us-them) | paired vs start (t) | per opponent wins |")
        L.append("|---|---|---|---|---|---|---|")
        for t in table:
            pv = f"{t.get('paired_vs_start', 0):+.3f} ({t.get('paired_t', 0):.1f})" if "paired_vs_start" in t else "-"
            L.append(f"| {t['name']} | {t['reward']:+.3f} | {100 * t['winrate']:.1f}% (n{t['n']}) | {t['gems']:.0f}-{t['gems_opp']:.0f} | "
                     f"{t['deaths']:.1f}-{t['deaths_opp']:.1f} | {pv} | {', '.join(f'{o} {v}' for o, v in t['per_opponent'].items())} |")
        L.append(f"\n## Chosen: {out['chosen']} - changes vs the start point\n")
        if changed:
            L.append("| gene | block | from | to | note |")
            L.append("|---|---|---|---|---|")
            for n, c in changed.items():
                L.append(f"| {n} | {c['block']} | {c['from']} | {c['to']} | {c['note']} |")
        else:
            L.append("(none: the start point was not beaten)")
        L.append("\n## Generations\n")
        try:
            for l in open(os.path.join(self.out, "history.jsonl"), encoding="utf-8"):
                h = json.loads(l)
                L.append(f"- gen {h['gen']} blocks {h['blocks']}: best {h['best']} selection {h['selection']:+.3f} (n{h['n_sel']}), "
                         f"validation {h['validation']:+.3f} t={h['t']} (n{h['n_val']}) {'ACCEPTED' if h['accepted'] else ''} "
                         f"changes {json.dumps(h['changes'])}")
        except OSError:
            pass
        L.append("\n## Block bandit\n")
        for b, s in sorted(st["block_stats"].items()):
            L.append(f"- {b}: tries {s['tries']}, wins {s['wins']:.1f}")
        open(os.path.join(self.out, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        arc = os.path.join(ROOT, f"rl_results_{os.path.basename(self.out)}.tar.gz")
        with tarfile.open(arc, "w:gz") as tf:
            for f in ("best_params.json", "learned_distribution.json", "report.md", "history.jsonl", "games.jsonl", "state.json", "train.log"):
                p = os.path.join(self.out, f)
                if os.path.exists(p):
                    tf.add(p, arcname=os.path.join(os.path.basename(self.out), f))
        log(f"results: {self.out}/report.md, best_params.json, learned_distribution.json; archive {arc}")

    def autoscale(self, deadline):
        """Fast games and slow builds (each candidate is a compile): grow the per-generation evaluation until games take about
        3x the generation's builds, so acceptance decisions get sharper for the same build cost; at most 3x the defaults and
        never so large that fewer than ~6 generations fit in the budget."""
        a = self.a
        if a.scale != "auto":
            f = float(a.scale)
        else:
            spg = self.sec_per_game or 60.0
            wave = self.sec_per_wave or 120.0
            build = math.ceil((a.pop + 1) / self.build_jobs) * wave
            g0 = a.pop * a.rung1 + a.keep2 * a.rung2 + a.keep3 * a.rung3 + 2 * a.valid + a.rung1 + a.rung2 + a.rung3
            f = max(1.0, min(3.0, 3.0 * build / max(1.0, g0 * spg)))
            budget = max(600.0, deadline - time.time())
            while f > 1.0 and (g0 * f * spg + build) > budget / 6:
                f -= 0.1
            f = max(1.0, f)
            log(f"speed: {spg:.1f}s per game (all workers), {wave:.0f}s per build wave of {self.build_jobs}; generation builds ~{build / 60:.1f} min")
        if f != 1.0:
            a.rung1, a.rung2, a.rung3 = int(round(a.rung1 * f)), int(round(a.rung2 * f)), int(round(a.rung3 * f))
            a.valid, a.final = int(round(a.valid * f)), int(round(a.final * f))
        log(f"evaluation scale x{f:.2f}: rungs {a.rung1}/{a.rung2}/{a.rung3} cases, validation {a.valid}, championship {a.final}")

    # ----- main loop
    def run(self):
        a = self.a
        self.rng = random.Random(a.seed)
        if a.resume:
            self.out = os.path.abspath(a.resume)
            self.state = json.load(open(os.path.join(self.out, "state.json"), encoding="utf-8"))
            self.set_rng(self.state["rng"])
        else:
            run = time.strftime("%Y%m%d_%H%M%S")
            self.out = os.path.join(ROOT, "rl_results", run)
            os.makedirs(self.out, exist_ok=True)
            start = self.space.init_genome()
            self.state = {"version": 1, "gen": 0, "start": start, "incumbent": dict(start), "dist": self.space.init_dist(),
                          "cache": {}, "accepted": [], "runners": [], "block_stats": {}, "league": [], "hof": [], "seed": a.seed,
                          "args": vars(a)}
        LOG["fh"] = open(os.path.join(self.out, "train.log"), "a", encoding="utf-8")
        deadline = time.time() + a.hours * 3600
        log(f"project {ROOT}; base bot {self.base}; {len(self.space.genes)} genes in blocks {self.space.blocks}; {len(self.maps)} maps")
        log(f"{platform.platform()}; {self.cpu} CPUs -> {self.workers} parallel games, {self.build_jobs} parallel builds; budget {a.hours:.2f} h")
        r = subprocess.run([self.cambc, "--version"], capture_output=True, text=True)
        log(f"cambc: {r.stdout.strip() or r.stderr.strip()}")
        # toolchain check: the start point alone first (the first build may download the toolchain)
        start_bot = self.genome_bot(self.state["start"])
        self.build([start_bot])
        if not self.built.get(start_bot):
            raise SystemExit(f"the base bot does not build: see {self.out}/build_logs/{start_bot}.log")
        self.setup_league()
        self.build([L["bot"] for L in self.state["league"]])
        self.state["league"] = [L for L in self.state["league"] if self.built.get(L["bot"])]
        self.save()
        # calibration: one batch of start-point games (also the first incumbent cache)
        if self.sec_per_game is None:
            cases = self.sample_cases(max(2, min(self.workers, 8)), [])
            self.run_games([(start_bot, c) for c in cases])
        self.autoscale(deadline)
        while not STOP["gens"]:
            spg = self.sec_per_game or 60.0
            gen_games = a.pop * a.rung1 + a.keep2 * a.rung2 + a.keep3 * a.rung3 + 2 * a.valid + a.rung1 + a.rung2 + a.rung3
            gen_time = gen_games * spg + 240
            final_time = 4 * a.final * spg + 300
            left = deadline - time.time()
            if left < gen_time + final_time:
                log(f"time left {left / 60:.0f} min < next generation {gen_time / 60:.0f} min + championship {final_time / 60:.0f} min: finishing")
                break
            if a.max_gens and self.state["gen"] >= a.max_gens:
                break
            self.generation()
        self.championship()  # also after a first Ctrl-C (a second one aborts)
        self.write_results()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=float, default=3.5, help="wall-clock budget for this session (default 3.5)")
    ap.add_argument("--base", default=None, help="bot directory under bots/ to train (default from knowledge.json: bb4)")
    ap.add_argument("--workers", type=int, default=0, help="parallel games (default: CPUs - 2, limited by free memory)")
    ap.add_argument("--build-jobs", type=int, default=0, help="parallel bot builds (default: CPUs / 3)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--pop", type=int, default=12, help="candidates per generation")
    ap.add_argument("--blocks-per-gen", type=int, default=2)
    ap.add_argument("--max-flips", type=int, default=3, help="switch / category genes a candidate may change at once")
    ap.add_argument("--rung1", type=int, default=8, help="cases per candidate in the first race rung")
    ap.add_argument("--keep2", type=int, default=4)
    ap.add_argument("--rung2", type=int, default=16)
    ap.add_argument("--keep3", type=int, default=2)
    ap.add_argument("--rung3", type=int, default=24)
    ap.add_argument("--valid", type=int, default=40, help="fresh validation cases for the generation's best")
    ap.add_argument("--final", type=int, default=64, help="championship cases per finalist")
    ap.add_argument("--t-accept", type=float, default=1.28, help="one-sided t threshold to accept (1.28 = 90%%)")
    ap.add_argument("--lr", type=float, default=0.5, help="mean step toward the better half when nothing is accepted")
    ap.add_argument("--sigma-decay", type=float, default=0.85)
    ap.add_argument("--sigma-min", type=float, default=0.04)
    ap.add_argument("--pbil", type=float, default=0.3, help="switch / category probability learning rate")
    ap.add_argument("--game-timeout", type=int, default=1500, help="wall seconds per game")
    ap.add_argument("--max-gens", type=int, default=0)
    ap.add_argument("--scale", default="auto", help="evaluation size multiplier ('auto': from the measured game and build speed)")
    ap.add_argument("--keep-bots", action="store_true", help="keep every candidate bot directory")
    ap.add_argument("--resume", default=None, help="rl_results/<run> to continue")
    ap.add_argument("--smoke", action="store_true", help="tiny end-to-end check (~20-30 minutes)")
    a = ap.parse_args()
    if a.seed is None:
        a.seed = int(time.time()) % 100000
    if a.smoke:
        a.pop, a.rung1, a.keep2, a.rung2, a.keep3, a.rung3, a.valid, a.final, a.max_gens = 2, 2, 1, 1, 0, 0, 2, 2, 1
        a.scale = "1"
        a.hours = min(a.hours, 1.0)
    signal.signal(signal.SIGINT, on_signal)
    try:
        signal.signal(signal.SIGTERM, on_signal)
    except (AttributeError, ValueError):
        pass
    Trainer(a).run()


if __name__ == "__main__":
    main()
