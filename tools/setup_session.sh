#!/bin/bash
# New container: SDK, wasm toolchain and every bot the session-6/7 ledger cells use, rebuilt with the exact sources
# their ledger rows were played with (tools/ledger.py checks the source hash; the expected hashes are printed at the end).
#   tools/setup_session.sh            # everything (~3 min)
#   tools/setup_session.sh --bots     # bots only (SDK and toolchain already there)
set -e
cd "$(dirname "$0")/.."
if [ "$1" != "--bots" ]; then
	pip install -q cambc==3.0.4   # Oct 21 balance patch (Stellar, Heart of Ruin, Ren nerfs; Vesper, Vendetta, Tavi, Prism buffs); rows per engine: ledger/ (2.2.5), ledger_v3/ (3.0.1), ledger_v3_0_2/, ledger_v3_0_4/
	cambc init --yes . > /dev/null 2>&1 || true   # map refresh fails in the cloud (platform blocked): fine
	C="curl -sSL --cacert /root/.ccr/ca-bundle.crt"
	mkdir -p /root/.cache/cambc && pushd /root/.cache/cambc > /dev/null
	if [ ! -d wasi-sdk-33 ]; then
		$C -o wasi.tgz https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz
		tar xzf wasi.tgz && mv wasi-sdk-33.0-x86_64-linux wasi-sdk-33 && rm wasi.tgz
	fi
	if [ ! -d cmake-3.31.8-linux-x86_64 ]; then
		$C -o cmake.tgz https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-linux-x86_64.tar.gz
		tar xzf cmake.tgz && rm cmake.tgz
	fi
	if [ ! -x ninja-1.12.1-linux-x86_64/ninja ]; then
		$C -o ninja.zip https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux.zip
		mkdir -p ninja-1.12.1-linux-x86_64 && (cd ninja-1.12.1-linux-x86_64 && python3 -c "import zipfile;zipfile.ZipFile('../ninja.zip').extractall('.')" && chmod +x ninja)
		rm ninja.zip
	fi
	popd > /dev/null
	git fetch -q --unshallow origin 2>/dev/null || true   # snapshots need old commits
fi
T=$(mktemp -d)
# _rm = legend_rm as shipped (60d9930); _ST = legend_st + 2 inert switches (cd4e2aa)
tools/snapshot.sh _rm 60d9930
tools/snapshot.sh _ST cd4e2aa
# The archetypes were built from _rm + the build_style 3/4 code of 78c32bf (brain.cpp only, no LEGEND_RUNTIME_PARAMS)
git diff 60d9930 78c32bf -- bots/legend/src/brain.cpp > $T/bs_brain.diff
SRC=bots/_rm tools/variant.sh _leg1 > /dev/null && (cd bots/_leg1/src && patch -s -p4 --no-backup-if-mismatch < $T/bs_brain.diff)
SRC=bots/_leg1 tools/make_archetypes.sh > /dev/null
# _m2 = legend_m2 (shipped in session 7) = _rm + x_farm.patch + x_survive.patch as of cbe612b + three survive switches on
git show cbe612b:experiments/wip/x_farm.patch > $T/farm.patch
git show cbe612b:experiments/wip/x_survive.patch > $T/surv.patch
SRC=bots/_rm tools/variant.sh _m2 > /dev/null
(cd bots/_m2 && patch -s -p1 --no-backup-if-mismatch < $T/farm.patch && patch -s -p1 --no-backup-if-mismatch < $T/surv.patch)
# _m3 = _m2 with the agents' final defaults (farm _C5: join_reach 1.2; survive _svI: outmatch_solo_adv 0.45)
SRC=bots/_m2 tools/variant.sh _m3 join_reach=1.2f outmatch_solo_adv=0.45f > /dev/null
# _x_gp = _m2 + the give-up clock fix (experiments/wip/x_gp.patch); _m4 = legend_m4 (shipped) = _x_gp + the _m3 values
SRC=bots/_m2 tools/variant.sh _x_gp > /dev/null && (cd bots/_x_gp && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_gp.patch)
SRC=bots/_x_gp tools/variant.sh _m4 join_reach=1.2f outmatch_solo_adv=0.45f > /dev/null
# _fA/_fB/_fC = the archetypes rebuilt on legend_m4 code (_leg4 = _m4 + all of 78c32bf = bots/legend at the legend_m4 ship)
git diff 60d9930 78c32bf -- bots/legend/src/params.h > $T/bs_params.diff
SRC=bots/_m4 tools/variant.sh _leg4 > /dev/null && (cd bots/_leg4/src && patch -s -p4 --no-backup-if-mismatch < $T/bs_brain.diff && patch -s -p4 --no-backup-if-mismatch < $T/bs_params.diff)
PRESS="fight_margin=1.1f isolated_fight_adv=1.2f steal_hp_frac=0.4f enemy_half_penalty=4.f deny_bonus=0.4f"
SRC=bots/_leg4 tools/variant.sh _fA build_style=3 $PRESS gank_bag=15 q0_push=0.5f --define "LEGEND_DRAFT 8,4,3,0,9" > /dev/null
SRC=bots/_leg4 tools/variant.sh _fB build_style=4 max_join=0 deny_bonus=0.f --define "LEGEND_DRAFT 3,4,9,8,0" > /dev/null
SRC=bots/_leg4 tools/variant.sh _fC build_style=3 obj_min_attackers=1 $PRESS --define "LEGEND_DRAFT 4,10,5,3,8" > /dev/null
# _m4x = _m4 + x_exec.patch (strategy v2 A1/A2); _m5a = legend_m5 (session 8) = _m4x + the consistent A100 RL values (experiments/wip/rl_a100_m5a_args.txt)
SRC=bots/_m4 tools/variant.sh _m4x > /dev/null && (cd bots/_m4x && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_exec.patch)
SRC=bots/_m4x tools/variant.sh _m5a $(cat experiments/wip/rl_a100_m5a_args.txt) > /dev/null
# Session 8, agent proxy: _px = legend@61fdce4 (= _m5a + inert code) + x_px.patch; _px9 = the ladder-calibrated proxy;
# _x_px = _m5a + x_pxfix.patch; _xp4 = legend_m6 (shipped) = _x_px with px_mode=2 camp_in_fight=3
tools/snapshot.sh _px 61fdce4 > /dev/null && (cd bots/_px && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_px.patch)
SRC=bots/_px tools/variant.sh _px9 px_mode=2 --define "LEGEND_DRAFT 9,4,3,0,8" > /dev/null
SRC=bots/_m5a tools/variant.sh _x_px > /dev/null && (cd bots/_x_px && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_pxfix.patch)
SRC=bots/_x_px tools/variant.sh _xp4 px_mode=2 camp_in_fight=3 > /dev/null
# Session 9: _m7 = legend_m7 (shipped) = _xp4 + x_m7.patch (fight2's area casts from 5, aoe_cast5=3, + ci_health_first=0);
# _f2q = the reach-5 proxy (_px9 + x_f2.patch with aoe_cast5=3 open_first=1; one engage_angle hunk does not apply: fine)
SRC=bots/_xp4 tools/variant.sh _m7 > /dev/null && (cd bots/_m7 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_m7.patch)
# Session 10: _x_mt = _m7 + obj2's ring plan (x_o2.patch, off) + the top-team proxy code (x_proxy_mi.patch: official_map,
# per-map drafts, build styles 9/10); proxies _mite (2nd team) and _ifish (1st); _x_c1 = _x_mt + x_m8.patch (mapdraft 3,
# md_stampede, o2_ring 2); _m8 = legend_m8 (shipped) = _x_c1 with mapdraft=3 md_stampede=1 o2_ring=2 (ledger name also _cS3)
SRC=bots/_m7 tools/variant.sh _x_mt > /dev/null && (cd bots/_x_mt && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_o2.patch && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_proxy_mi.patch)
SRC=bots/_x_mt tools/variant.sh _mite mapdraft=1 build_style=9 o2_ring=1 o2_ring_melee=1 > /dev/null
SRC=bots/_x_mt tools/variant.sh _ifish mapdraft=2 build_style=10 > /dev/null
SRC=bots/_x_mt tools/variant.sh _x_c1 > /dev/null && (cd bots/_x_c1 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_m8.patch)
SRC=bots/_x_c1 tools/variant.sh _m8 mapdraft=3 md_stampede=1 o2_ring=2 > /dev/null
SRC=bots/_m8 tools/variant.sh _cS3 > /dev/null
# Session 11: _m9 = legend_m9 (shipped at the user's request, ideas from the default branch, all on) = _m8 + x_mi.patch
SRC=bots/_m8 tools/variant.sh _m9 > /dev/null && (cd bots/_m9 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_mi.patch)
# _m10 = legend_m10 (shipped) = _m9 with every mi_* switch off: plays legend_m8's games (86-87 of 88 identical)
MIOFF="mi_health_emblem=0 mi_learn_burst=0 mi_lethal=0 mi_cd_slack=0 mi_walk_cast=0 mi_endgame_bank=0 mi_learn_fight=0.f mi_learn_race=0 mi_island_bank=0 mi_recall_shop=0 mi_relaxed=0 mi_two_bodies=0 mi_deny_gems=0 mi_flip_guard=0 mi_kite=0 mi_chip=0 mi_close_in=0"
SRC=bots/_m9 tools/variant.sh _m10 $MIOFF > /dev/null
rm -rf $T
# S7R: _m11 = legend_m11 (shipped) = _m10 + experiments/wip/x_m11.patch (ward_bush 2 + the contest blob opening)
SRC=bots/_m10 tools/variant.sh _m11 > /dev/null && (cd bots/_m11 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_m11.patch)
# S7R: _fw = legend_m12 (shipped) = _m10 + experiments/wip/x_m12.patch (warding only on contest-type maps + the contest blob opening)
SRC=bots/_m10 tools/variant.sh _fw > /dev/null && (cd bots/_fw && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_m12.patch)
# _fc = legend_m12b (shipped) = _m10 + experiments/wip/x_m12b.patch (legend_m12 + contest plan only on 50x50 maps)
SRC=bots/_m10 tools/variant.sh _fc > /dev/null && (cd bots/_fc && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_m12b.patch)
# _x_pd / _x_pd2 = _fc + the parameter draft (experiments/wip/x_pd1.patch first version, x_pd.patch final); _pd2 = legend_m13 (shipped)
SRC=bots/_fc tools/variant.sh _x_pd > /dev/null && (cd bots/_x_pd && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_pd1.patch)
SRC=bots/_x_pd tools/variant.sh _pd mapdraft=6 > /dev/null
SRC=bots/_fc tools/variant.sh _x_pd2 > /dev/null && (cd bots/_x_pd2 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_pd.patch)
SRC=bots/_x_pd2 tools/variant.sh _pd2 mapdraft=6 > /dev/null
# _x_pg = _pd2 + experiments/wip/x_pg.patch (size-free ring and contest gates); _pg3 = legend_m14 candidate
SRC=bots/_pd2 tools/variant.sh _x_pg > /dev/null && (cd bots/_x_pg && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_pg.patch)
SRC=bots/_x_pg tools/variant.sh _pg3 o2_ring=3 mono_size50=2 pd_obj_multi=1 > /dev/null
# Session 13: _ch2 = legend_m14_commit (the main bot from Oct 19) = the zip's sources exactly (hash 5f24a1979ddc);
# _x_ic = _pg3 + x_ic.patch (all session-12 switches, off); _x_sn / _snk = the sneaky-bush proxy (x_sn.patch on _m10)
mkdir -p bots/_ch2 && rm -rf bots/_ch2/src && (cd bots/_ch2 && python3 -c "import zipfile;zipfile.ZipFile('../../submissions/history/legend_m14_commit_20261019.zip').extractall('.')") && cp bots/legend/.gitignore bots/_ch2/
SRC=bots/_pg3 tools/variant.sh _x_ic > /dev/null && (cd bots/_x_ic && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_ic.patch)
SRC=bots/_m10 tools/variant.sh _x_sn > /dev/null && (cd bots/_x_sn && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_sn.patch)
SRC=bots/_x_sn tools/variant.sh _snk mapdraft=4 build_style=9 > /dev/null
# Session 13 (patch 3.0): _mlkc40 = legend_m15 exactly (the zip minus the inert LEGEND_RUNTIME_PARAMS block, hash 8eb9563d0d5b);
# god / _g4 = GOD v2 (submissions/god.zip = history/god_v2_20261020.zip, hash 19a1785457d3). god is the working copy.
mkdir -p bots/_mlkc40 && rm -rf bots/_mlkc40/src && (cd bots/_mlkc40 && python3 -c "import zipfile;zipfile.ZipFile('../../submissions/history/legend_m15_20261020.zip').extractall('.')" && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/m15zip_to_mlkc40.patch) && cp bots/legend/.gitignore bots/_mlkc40/
for g in _g4 god; do [ "$g" = god ] && [ -d bots/god/src ] && continue; mkdir -p bots/$g && rm -rf bots/$g/src && (cd bots/$g && python3 -c "import zipfile;zipfile.ZipFile('../../submissions/history/god_v2_20261020.zip').extractall('.')") && cp bots/legend/.gitignore bots/$g/; done
for b in _mlkc40 _g4 god; do cambc build $b > /dev/null && echo "built $b"; done
# Session 14 (GOD v8, cambc 3.0.2): GOD v7 = history/god_v7_20261020.zip (hash 763b1c081f8a); _g8s = v7 with hor_strike written 1 (the v7 ledger
# rows, 152375f0f792); the sparring proxies _pw, _pc, _ph, _pws = v7 + experiments/proxies/<name>.patch (built from earlier working copies;
# _pws = Heart of Ruin, Ren, Stellar, Ryth, Varg forced with Power builds and the striking Heart of Ruin); _x_v8 = v7 + experiments/wip/x_v8.patch.
v7() { mkdir -p bots/$1 && rm -rf bots/$1/src && (cd bots/$1 && python3 -c "import zipfile;zipfile.ZipFile('../../submissions/history/god_v7_20261020.zip').extractall('.')") && cp bots/legend/.gitignore bots/$1/; }
v7 _g8s && sed -i 's/int hor_strike = SDK_HAS_HOR ? 1 : 0;/int hor_strike = 1;/' bots/_g8s/src/params.h
for p in _pw _pc _ph _pws _pm; do v7 $p && (cd bots/$p && patch -s -p1 --no-backup-if-mismatch < ../../experiments/proxies/$p.patch); done
[ -d bots/_x_v8/src ] || { v7 _x_v8 && (cd bots/_x_v8 && patch -s -p1 --no-backup-if-mismatch < ../../experiments/wip/x_v8.patch); }
mkdir -p bots/_m15 && rm -rf bots/_m15/src && cp -r bots/legend/src bots/_m15/ && cp bots/legend/.gitignore bots/_m15/   # _m15 = legend_m15 (bots/legend, ledger name of the v6-v8 cells)
for b in _g8s _pw _pc _ph _pws _pm _m15 _x_v8; do cambc build $b > /dev/null && echo "built $b"; done
for b in _pg3 _ch2 _snk _pd2 _pd _fc _fw _m11 _rm _ST _m2 _m3 _x_gp _m4 _m4x _m5a _px9 _xp4 _m7 _fA _fB _fC _mite _ifish _m8 _cS3 _m9 _m10 legend idle; do cambc build $b > /dev/null && echo "built $b"; done
python3 - <<'EOF'
import sys; sys.path.insert(0, 'tools'); import ledger
want = {'_pm': 'dc55f8d8ba35', '_m15': '7f1fbbaa8fa8', '_g8s': '152375f0f792', '_pw': '827ab7268c47', '_pc': '79a41047e8e1', '_ph': '23077c2e8e95', '_pws': '1bc4daa14baf', '_mlkc40': '8eb9563d0d5b', '_g4': '19a1785457d3', '_rm': '339a961d3427', '_ST': 'ca21cbfe785b', '_eA': '0ee193334b60', '_eB': '654605b27deb', '_eC': '116ccc8b53b1',
		'_m2': '1684aa2a482c', '_m3': '86c9e8f3de35', '_x_gp': '92e199947185', '_m4': '0dc2a2aac28a',
		'_m5a': '5620bb02867a', '_xp4': '6a1a52e4ddb8', '_m7': '61dd9019869d', '_mite': '688b37be81e3', '_ifish': '6fde429be694', '_m8': '540e17bfe5a4', '_cS3': '540e17bfe5a4', '_m9': '0df32fa5ee2d', '_m10': 'a0e6030bf0f4', '_m11': '0dd8010eaf12', '_fw': '104743e4f1d5', '_fc': '531e7331a283', '_pd': '8ede6d7d3aa1', '_pd2': 'c8272a7e1846', '_pg3': 'cdc6dc9027f3', '_ch2': '5f24a1979ddc', '_snk': '70c95c1095f6', '_fA': '25fe5950b034', '_fB': 'f8e472c342f3', '_fC': 'ef5391dcc92b'}
for b, h in want.items():
	got = ledger.src_hash(b)
	print(f'{b:5s} {got} {"ok" if got == h else "MISMATCH (expected " + h + ")"}')
EOF
