"""Per-team economy in the v20 games vs the top 3: captured gems / captures, first capture round, deaths and bag lost, kills,
banked gems, bank trips, attacks on champions vs camps, captures with 2+ allies near, rounds alive.
    python3 -I econ.py"""
import collections, gzip, json
IDX = [('/tmp/claude-0/ic_all4.json', {'v20'}), ('/tmp/claude-0/top3/index.json', {'mite', 'tk'})]
A = collections.defaultdict(collections.Counter)
for ip, sets in IDX:
    for p, v in json.load(open(ip)).items():
        st = v['set']
        if st not in sets:
            continue
        st = 'ic' if st == 'v20' else st
        d = json.load(gzip.open(p))
        o = v['ours']
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        fc = {0: None, 1: None}
        for e in d['events']:
            k = e['k']; t = e.get('team')
            if t is None and 'who' in e:
                t = team.get(e['who'])
            if t is None:
                continue
            w = 'us' if t == o else 'them'
            c = A[(st, w)]
            if k == 'CaptureGems':
                c['cap_gems'] += e['gems']; c['caps'] += 1; c['cap_gold'] += e.get('gold', 0)
                if fc[t] is None: fc[t] = e['r']
                if e['r'] < 300: c['cap300'] += e['gems']
                elif e['r'] < 800: c['cap800'] += e['gems']
                else: c['caplate'] += e['gems']
            elif k == 'Death':
                c['deaths'] += 1; c['bag_lost'] += e.get('bag', 0)
                A[(st, 'them' if w == 'us' else 'us')]['kills'] += 1
            elif k == 'Banked':
                c['banked'] += e['gems']; c['banks'] += 1
            elif k == 'Shop':
                c['shops'] += 1
            elif k == 'Teleport channel':
                c['tele'] += 1
            elif k == 'Place ward':
                c['wards'] += 1
        for t in (0, 1):
            w = 'us' if t == o else 'them'
            A[(st, w)]['games'] += 1
            A[(st, w)]['first_cap'] += fc[t] or 2000
            A[(st, w)]['final'] += d['meta']['submitted'][t]
keys = ['final', 'cap_gems', 'cap300', 'cap800', 'caplate', 'caps', 'cap_gold', 'first_cap', 'banked', 'banks', 'deaths', 'bag_lost', 'kills', 'shops', 'wards', 'tele']
print(f"{'':10s}" + ''.join(f"{k:>9s}" for k in keys))
for st in ('ic', 'mite', 'tk'):
    for w in ('us', 'them'):
        c = A[(st, w)]; g = c['games']
        print(f"{st + ' ' + w:10s}" + ''.join(f"{c[k] / g:9.1f}" for k in keys))
