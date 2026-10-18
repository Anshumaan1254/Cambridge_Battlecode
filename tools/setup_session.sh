#!/bin/bash
# New container: SDK, wasm toolchain and every bot the session-6/7 ledger cells use, rebuilt with the exact sources
# their ledger rows were played with (tools/ledger.py checks the source hash; the expected hashes are printed at the end).
#   tools/setup_session.sh            # everything (~3 min)
#   tools/setup_session.sh --bots     # bots only (SDK and toolchain already there)
set -e
cd "$(dirname "$0")/.."
if [ "$1" != "--bots" ]; then
	pip install -q cambc==2.2.5
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
rm -rf $T
for b in _rm _ST _m2 _m3 _x_gp _m4 _m4x _m5a _px9 _xp4 _m7 _fA _fB _fC _mite _ifish _m8 _cS3 _m9 legend idle; do cambc build $b > /dev/null && echo "built $b"; done
python3 - <<'EOF'
import sys; sys.path.insert(0, 'tools'); import ledger
want = {'_rm': '339a961d3427', '_ST': 'ca21cbfe785b', '_eA': '0ee193334b60', '_eB': '654605b27deb', '_eC': '116ccc8b53b1',
		'_m2': '1684aa2a482c', '_m3': '86c9e8f3de35', '_x_gp': '92e199947185', '_m4': '0dc2a2aac28a',
		'_m5a': '5620bb02867a', '_xp4': '6a1a52e4ddb8', '_m7': '61dd9019869d', '_mite': '688b37be81e3', '_ifish': '6fde429be694', '_m8': '540e17bfe5a4', '_cS3': '540e17bfe5a4', '_m9': '0df32fa5ee2d', '_fA': '25fe5950b034', '_fB': 'f8e472c342f3', '_fC': 'ef5391dcc92b'}
for b, h in want.items():
	got = ledger.src_hash(b)
	print(f'{b:5s} {got} {"ok" if got == h else "MISMATCH (expected " + h + ")"}')
EOF
