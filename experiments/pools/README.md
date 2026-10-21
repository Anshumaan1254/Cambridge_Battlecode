# Map pools of the A/B protocol (session 14, Oct 21)

- `all308.csv`: every distinct map layout under `maps/` (327 files minus tile-identical copies; `zz_test` dropped), comma-separated paths
  as `tools/ledger.py run --maps` takes them. `fingerprints327.txt`: one line per file, a hash of its tiles and camps, then the path
  (copies share the hash: `maps/ladder` = `maps/comp`, `maps/cl` and 3 of `maps/ct` = `maps/var17`, `p30/contest_p` = contest).
- `train156.csv` / `test152.csv`: a fixed split of `all308` made before any 3.0.4 game. Every tuning screen uses the train half only;
  a candidate is confirmed on the test half, then on all 308 maps (616 games, both sides).
- Read a cell with `python3 tools/abstat.py BOT OPP --pool experiments/pools/test152.csv [--by-dir]`.

`train78a.csv` / `train78b.csv` (Oct 21): the even / odd entries of `train156.csv` (78 maps each). Stage-1 screens of single switches
run on `train78a` (156 games); a candidate that passes is completed on `train78b`, then confirmed on `test152` and `all308`.
