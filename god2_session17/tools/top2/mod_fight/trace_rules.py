# mod_fight: rule counts from the G2F trace lines of a debug build (combat() prints one line per turn with an enemy in sight).
#   python tools/top2/mod_fight/trace_rules.py BUNDLE_OR_STDOUT [...]     (a cambc run bundle .repl26a zip, or an extracted team stdout)
# Codes: 0 god2 (no rule), 10 kill this turn (god2), 2/3/4 ml2 exit / ml2 walk-away / ml2 hold over a rule, 11 C1 start gate blocks god2,
# 31/32 C3 leave (own health / ch), 33 C3 keep fighting, 34 C3 target runs, chase off: convert, 35 C3 retarget to an enemy that stays,
# 41/42 fight moved beyond 4: chase allowed / off, 43 start gate beyond 4, 44 farm on, 81 C8 keep farming (5-8), 82 C8 fight,
# 83 C8 leave, 84 C8 finish the group, 85/86 C8 0.6-0.9 fight / leave, 87 C8 ch >= 0.9 but the start gate blocks: farm,
# 89 C8 5-8 below g2f_far_min: god2, 91 C9 no walking deeper; +100 spawn guard, +200 bag / win_bank guard.
import collections, io, re, sys, zipfile
tot = collections.Counter()
acts = collections.Counter()
for f in sys.argv[1:]:
    if f.endswith('.repl26a'):
        z = zipfile.ZipFile(f)
        txt = ''.join(z.read(n).decode('utf-8', 'replace') for n in z.namelist() if n.endswith('.stdout'))
    else:
        txt = open(f, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'G2F r=\d+ b=\d+ ch=\d+ rule=(\d+) act=(\d+)', txt.replace('\x00', '')):
        tot[int(m.group(1))] += 1
        acts[int(m.group(2))] += 1
n = sum(tot.values())
print('turns with an enemy in sight:', n)
for k, v in sorted(tot.items()):
    print('  rule %3d: %6d (%.1f%%)' % (k, v, 100 * v / max(1, n)))
print('acts:', ' '.join('%d:%d' % kv for kv in sorted(acts.items())))
