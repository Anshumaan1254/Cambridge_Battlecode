# ladder_loop.py: the ladder A/B loop

`experiments/ladder_nov2/ladder_loop.py` automates the loop: take a snapshot, deploy a candidate, replay paired
unranked groups, get a verdict, then keep or roll back. It is Python 3 with the standard library only. Run it from
the repo root (`/home/claude/cambridge_battlecode`); it also works from elsewhere, because paths resolve relative to
the script.

**Safety.** Only three commands change anything on the platform: `cambc submit`, `cambc submissions activate`
and `cambc match-groups create`. They run only with `--execute`; without it, the tool prints the exact command as
`[dry-run] ...` and changes nothing (not even local files). Every external command goes through one helper,
`run_cmd()`, which logs it to stderr with its exit code and duration (`$ cambc ...`, or `WRITE $ ...` for the three
write commands). Read-only calls are retried with back-off. Write commands are never retried, so a flaky network
cannot double-submit.

## The loop

```bash
L="python3 experiments/ladder_nov2/ladder_loop.py"
$L snapshot                                        # rank, rating, live version, ranked record since it went live
$L deploy god23 --note "GOD v23 fight engine"      # dry run: prints the commands
$L deploy god23 --note "GOD v23 fight engine" --execute   # previous -> state, submit, wait for the build (15 min), activate
$L paired-run --plan experiments/ladder_nov2/paired_plan_v85.json --max 20 --execute    # replay the old version's groups
$L paired-report --plan experiments/ladder_nov2/paired_plan_v85.json                    # ~30 min later
$L verdict                                         # KEEP / ROLLBACK / WAIT, with the reasoning
$L rollback --execute                              # only if the verdict says ROLLBACK
```

To make a paired plan for the version that is live now, before you deploy, run
`python3 tools/paired_groups.py plan experiments/ladder_nov2/matches_me.jsonl --since <its activation ISO> > experiments/ladder_nov2/paired_plan_v<N>.json`.
Name the file `..._v<N>.json` after the version that played the originals: `paired-run` refuses to replay a plan
while that same version is live, because deterministic games would give identical results.

## Files

| file | what |
|---|---|
| `loop_state.json` | `current` (version, activatedAt, rank and rating at activation), `previous`, `pending` (an upload not activated yet), `plan` (the last plan `paired-run` used), `history`. It is written only by `deploy`, `rollback`, `adopt` and `paired-run` with `--execute`. |
| `loop_log.md` | One line per `snapshot`, plus a `DEPLOY` / `ROLLBACK` line per switch, all tagged `\| ladder_loop`. `ladder_check.py` writes to the same file. |
| plan JSON | The `tools/paired_groups.py plan` format. `paired-run` adds `new_group`, `new_version` and `new_queued_at` to each group it queues, saving after every group; `paired_groups.py report` still reads the file. |
| `matches_me.jsonl` | The cache that `fetch_me.py` maintains. `paired-report` and `verdict` refresh it first with `fetch_me.py --pages 3`; skip that with `--no-refresh`. |

`--state PATH` and `--log PATH` work on every command, which is handy for test copies.

## Commands

- **`snapshot [--since ISO] [--no-log]`**: our rank and rating, plus the ranked games since the live version went
  live. For those games it shows W/N, the Elo-expected score (our current rating against each opponent's current
  rating, as `ladder_check.py` computes it), the excess, z, the performance rating and the results by opponent-rating
  band. It appends that line to `loop_log.md`. Ranked games come straight from `cambc matches list --kind ranked`,
  paging back to the activation time.
- **`adopt [--since ISO] [--previous N]`**: records a version that went live outside this tool, such as v85 (made
  live by the user's other session), so that `verdict` and `rollback` work for it. Without `--since` it accepts only
  an unambiguous case: exactly one version switch since the live version was uploaded. The state file is local, so
  `adopt` needs no `--execute`.
- **`deploy BOT --note "..." [--execute]`** runs these steps, where BOT is a directory under `bots/` and the note has
  at most 80 characters:
  1. Refuse if the platform is frozen.
  2. Record the live version as `previous`, carrying over its activation time from the state file.
  3. Run `cambc submit BOT -n NOTE`.
  4. Poll `cambc submissions list --json` (every `--poll`, default 15 s, up to `--timeout`, default 900 s). Statuses
     `inactive` and `active` count as built, anything containing fail, error or reject as failed, and anything else
     as still building.
  5. Read the ladder, run `cambc submissions activate N --json`, and confirm that N is live.
  6. Record `current`: the version, its activation time, and our rank and rating at activation.
  7. Append a `DEPLOY` line to `loop_log.md`.

  After a failed build, nothing is pending. After a timeout or a failed activation, the upload stays `pending`:
  `deploy --resume --execute` waits for it and activates it, without uploading again. A new deploy is refused while
  an upload is pending, unless you pass `--force`.
- **`paired-run --plan P --max N [--execute] [--force] [--sleep S]`**: reads `cambc match-groups quota --json`
  (`quota.used` / `quota.limit` / `resetsAt`, `ready`, `requesterRank`, `maxRankGap`, `opponentRanks`), then queues
  up to min(N, remaining quota) groups that have not been run. Each command is
  `cambc match-groups create OPP --source-group G --maps m1,..,m5 --sides s1,..,s5 --json`. On a quota or rate-limit
  error it stops politely and prints the reset time; run the same command again later, and it skips the groups
  already queued. It stops after 3 other failures in a row. The id of a new group is read from the JSON in the
  output. If no id can be found, `new_group` is set to `?` and `paired-report` finds the group by opponent, maps and
  sides.
- **`paired-report --plan P [--since ISO] [--no-refresh]`**: one line per replayed group: the old and new results
  (W/L, `.` = still pending) and the flipped games (`+map/side` for L->W, `-map/side` for W->L). Then the totals per
  replaying version: old record, new record, flips, net and the sign-test p. Groups missing from the cache come from
  `cambc match-groups show` (at most `--show-max` calls). It ends with the ranked comparison described below.
- **`verdict [--plan P]`**: the same data, then the decision. It uses `--plan`, or else the plan the last
  `paired-run` recorded. Options: `--verbose` (per-group lines), `--min-games 60`, `--p 0.2`, `--z 1.5`.
- **`rollback [--execute] [--to N] [--force]`**: activates `previous` and records the version it rolled back from
  as `previous` with `rolledBack: true`. A second plain `rollback` therefore refuses instead of re-activating the
  bad version; use `--to N` to choose a version explicitly. It also refuses when the live version is not the one the
  state file recorded (someone switched by hand), unless you pass `--to` or `--force`.

## When did the live version go live?

**The live submission's `statusAt` is not its activation time.** The platform keeps moving it while the version
stays live. On Nov 2, v85 went live at about 21:15:46Z, which is when v84 went inactive. Its `statusAt` read
23:15:54Z, then 23:30:54Z, then 23:35:57Z, with no version switch in between. Inactive versions keep their
`statusAt`.

So the tool picks the start of the "new" window in this order:

1. `--since ISO`.
2. The state file, written by `deploy`, `rollback` or `adopt`.
3. The **last version switch seen**: another version's status change after the live version was uploaded. The
   previous version's window then ends at the **first** switch seen, and games between the two switches count for
   neither version. The tool prints a warning that lists the switches.
4. `statusAt`, as a last resort, also with a warning.

When case 3 sees two or more switches, the window is a guess. `snapshot` and `paired-report` still print the
numbers, but `verdict` does not use the ranked signal: after a manual rollback, the "first switch" can belong to
older history, and the baseline would then be the wrong version.

With today's data, case 3 reports two switches: v84 went inactive at 21:15:46Z, and v73 "THE ULTIMATE GPTA"
changed status at 22:56:35Z. If v73 was really live for a while, the games between 21:15 and 22:56 are not all
v85's. The coordinator says v85 has been live since about 21:15. If that is right, record it once:
`$L adopt --since 2026-11-02T21:15:46Z --previous 84`.

Windows always use a game's **creation** time. A game created before the switch but finished after it counts for
neither version.

## The statistics behind `verdict`

- **Paired replays.** For each replayed game (same opponent bot version, map and side), the tool compares the old
  result with the new one. Flips are L->W (good) and W->L (bad). The sign test is a two-sided exact binomial test on
  the flips (n = flips, p = 1/2). "Paired games" counts the games where both results are known. The verdict uses
  only replays played by the live version: the `new_version` recorded at queue time or, for groups queued by
  another tool, games created after the live version went live.
- **Ranked.**
  - *New window:* the live version's ranked games since it went live.
  - *Old window:* the previous version's last `--prev-n` (100) ranked games before that, never earlier than its own
    activation when the state file knows it, or `--prev-since`.
  - *Ratings:* opponents are rated at their current ladder rating, and teams no longer on the ladder are left out.
  - *Baseline:* the previous version's performance rating P0 over the old window, i.e. the rating whose Elo
    expectation equals its actual wins. The expected wins of the new games at P0 are E = Σ E(P0, r_i).
  - *SE:* `SE = sqrt(V1 * (1 + V1/V0))`, where V = Σ E(1-E). The second term is P0's own noise. The z-score is
    `z = (wins - E) / SE`.
  - *Fallback:* with fewer than 30 old games, the baseline is the rating recorded at activation and `SE = sqrt(V1)`.
  - *Also printed:* both performance ratings and the raw two-proportion z.
- **Decision.** Thresholds are flags: `--min-games 60 --p 0.2 --z 1.5`.
  - **ROLLBACK**: the paired flips are net negative with p < 0.2 over at least 60 paired games, **or** the ranked
    z < -1.5 after at least 60 ranked games.
  - **KEEP**: the same thresholds, net positive.
  - **WAIT**: anything else.
  - ROLLBACK takes precedence when the two signals disagree; the output says so.
  - Ranked games arrive at about 30 an hour (one group of 5 every 10 minutes), so 60 ranked games take about 2 hours.
    12 replayed groups give 60 paired games.

## Formats not verified against real output

These outputs were not seen for real, because those commands were never run. The tool handles them defensively:

- **What `cambc submit` prints.** The tool takes the version from "version N" or "vN" when N is newer than every
  earlier version. Otherwise it identifies the upload in the build poll by its note, or else as the first new
  version since the submit.
- **The JSON of `cambc match-groups create --json`.** The tool looks for `groupId` / `matchGroupId` / `id` at any
  depth, then for any UUID other than the opponent's id and the source group's id, then falls back to `?` plus
  recovery by opponent, maps and sides.
- **The exact wording of quota errors.** The tool matches quota, rate limit, too many, 429, exceeded and similar
  words.
- **Status strings while a build runs, or after a failed one.**

## How it was tested

- **Pure functions:** unit tests for time parsing, Elo, performance rating, the sign test, version and group-id
  parsing, the window boundaries and pairing.
- **Read-only paths, for real:** snapshot (default window and `--since`), paired-report and verdict on
  `paired_plan_v84.json`, and on a scratch plan built from 12 real replayed groups (pairing, flips, `?`-id recovery,
  the `match-groups show` fallback, version gating).
- **Write paths in dry-run:** deploy, deploy `--resume`, paired-run and rollback.
- **The `--execute` paths** (deploy, build failure, timeout plus `--resume`, rollback and its double-rollback guard,
  paired-run with a quota error after 2 groups) were run only against a fake `cambc` in a PATH without the real
  one, with scratch state, log and plan files. None of them has run against the platform.
