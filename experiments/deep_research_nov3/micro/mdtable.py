"""Markdown fingerprint tables from feats.json (value with n)."""
import json
F = json.load(open('/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/feats.json'))
lad = sorted([t for t in json.load(open('/home/claude/cambridge_battlecode/experiments/top30_nov3/ladder.json'))['teams'] if t['rank'] <= 30], key=lambda t: t['rank'])
def c(lab, k, sc=100, f='{:.0f}', n=True):
    v = F.get(lab, {}).get(k)
    if not v or v[0] is None: return '-'
    return f.format(v[0] * sc) + (f' ({v[1]})' if n else '')
A = [('exch_g','exch/g',1,'{:.1f}',False),('open','open% (exch)',100,'{:.0f}',True),('open_R_med','open R med',1,'{:.2f}',False),
     ('open_weak','open at R<0.67 %',100,'{:.0f}',False),('ct_fight_weak','contact: fight% R<0.67 (n)',100,'{:.0f}',True),
     ('ct_fight_strong','contact: fight% R>1.5 (n)',100,'{:.0f}',True),('xwin','exch win% (n)',100,'{:.0f}',True),
     ('xwin_par_eqitem','win% R 0.67-1.5, gap<=3 (n)',100,'{:.0f}',True),('g_kill','K/g',1,'{:.1f}',False),('g_n','D/g',1,'{:.1f}',False),
     ('g_walkin','D walk-in/g',1,'{:.1f}',False),('g_caught','D caught/g',1,'{:.1f}',False),('g_respawn','D <=40r after respawn/g',1,'{:.1f}',False)]
B = [('ret_dash_used','retreat dash% (n)',100,'{:.0f}',True),('ret_dash_used_HoR','HoR retreat dash% (n)',100,'{:.0f}',True),
     ('ret_died8','retreat caught% (n)',100,'{:.0f}',True),('focus','focus% (hits)',100,'{:.0f}',True),
     ('pick_low_lift','low-hp lift (n)',1,'{:+.2f}',True),('pick_carrier_lift','carrier lift (n)',1,'{:+.2f}',True),
     ('spell_d4','spell from 4 % (n)',100,'{:.0f}',True),('stun_followed','stun followed% (n)',100,'{:.0f}',True),
     ('part_alone','alone% (parts)',100,'{:.0f}',True),('dash_engage_HeartOfRuin','HoR dash in% (n)',100,'{:.0f}',True),
     ('hor_dash_hit','HoR dash hits% (n)',100,'{:.0f}',True),('marc_enh_champ_nearfoe','Marc enh on champ% (n)',100,'{:.0f}',True)]
out = []
for name, cols in (('A. Engagement, exchanges, deaths', A), ('B. Retreat, targeting, champion micro', B)):
    out.append(f'**Table {name}**\n')
    out.append('| # | team | rating | games | ' + ' | '.join(x[1] for x in cols) + ' |')
    out.append('|' + '---|' * (4 + len(cols)))
    for t in lad:
        lab = t['teamId'][:8]
        g = F.get(lab, {}).get('games', [0])[0]
        out.append(f"| {t['rank']} | {t['name'][:22]} | {round(t['rating'])} | {g:.0f} | " + ' | '.join(c(lab, k, sc, f, n) for k, _, sc, f, n in cols) + ' |')
    for lab, nm in (('R01-10','ranks 1-10'),('R20-30','ranks 20-30'),('TOPl','top-30 losing sides'),('US84','US v84'),('OPP84','OPP v84 (same games)'),('US88','US v88 (all losses)'),('OPP88','OPP v88 (same games)')):
        g = F.get(lab, {}).get('games', [0])[0]
        out.append(f"| | **{nm}** | | {g:.0f} | " + ' | '.join(c(lab, k, sc, f, n) for k, _, sc, f, n in cols) + ' |')
    out.append('')
open('/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/fingerprint_tables.md', 'w').write('\n'.join(out))
print('ok', len(out))
