# Aggregate tools/top2/fights/trib_ctx.mjs output: when do teams start big tributes (bag >= 60), with what score, and how they end.
#   python tools/top2/fights/trib_agg.py C:/battlecode/cache/top2_fights
import json, os, sys
import pandas as pd
D = sys.argv[1]
rows = []
for k in ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']:
    for l in open(os.path.join(D, f'trib_{k}.jsonl'), encoding='utf-8'):
        g = json.loads(l)
        for t in g.get('trib', []):
            rows.append({'key': k, 'game': g['game'], 'map': g['map'], 'win': g['win'], **t})
T = pd.DataFrame(rows)
T.to_pickle(os.path.join(D, 'flat', 'trib.pkl'))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
T['prism'] = T.ty == 'Prism'
T['bb'] = pd.cut(T.bag, [60, 100, 200, 400, 100000], labels=['60-99', '100-199', '200-399', '400+'], right=False)
print('## Tributes with bag >= 60: outcome by bag size (pooled S / O)')
print(T.groupby(['grp', 'bb'], observed=True).agg(n=('bag', 'size'), done=('res', lambda s: (s == 'done').mean()), killed=('res', lambda s: (s == 'killed').mean()),
      stunned=('res', lambda s: (s == 'stunned').mean()), locked=('res', lambda s: (s == 'locked').mean()), cancel_near=('res', lambda s: (s == 'cancel_enemy_near').mean()),
      cancel_other=('res', lambda s: (s == 'cancel').mean()), enemy8=('n8', lambda s: (s > 0).mean()), wins_game=('wins', 'mean'), after2000=('endsAfter2000', 'mean')).round(2).to_string())
print('\n## Prism tributes >= 100 per study team (S) and their opponents (O)')
x = T[T.prism & (T.bag >= 100)]
print(x.groupby(['key', 'grp']).agg(n=('bag', 'size'), bag_med=('bag', 'median'), r_med=('r', 'median'), score_med=('score', 'median'), escore_med=('escore', 'median'),
      would_win=('wins', 'mean'), done=('res', lambda s: (s == 'done').mean()), enemy8=('n8', lambda s: (s > 0).mean()), closest_med=('closest', 'median'),
      killed=('res', lambda s: (s == 'killed').mean()), stunned=('res', lambda s: (s == 'stunned').mean()), locked=('res', lambda s: (s == 'locked').mean()),
      cancel_near=('res', lambda s: (s == 'cancel_enemy_near').mean()), after2000=('endsAfter2000', 'mean')).round(2).to_string())
print('\n## Do game-winning tributes complete? (bag + score >= 1000)')
print(T[T.bag >= 60].groupby(['grp', 'wins']).agg(n=('bag', 'size'), done=('res', lambda s: (s == 'done').mean()), enemy8=('n8', lambda s: (s > 0).mean())).round(2).to_string())
print('\n## Prism >= 100: completion when an enemy is within 8 at the start vs not')
print(x.groupby(['grp', x.n8 > 0]).agg(n=('bag', 'size'), done=('res', lambda s: (s == 'done').mean()), locked=('res', lambda s: (s == 'locked').mean()),
      stunned=('res', lambda s: (s == 'stunned').mean()), killed=('res', lambda s: (s == 'killed').mean()), near=('res', lambda s: (s == 'cancel_enemy_near').mean())).round(2).to_string())
print('\n## Repeated attempts: Prism >= 100 tribute starts per game (S) and bag gained before the first completed one')
y = x[x.grp == 'S'].groupby(['key', 'game']).agg(starts=('bag', 'size'), done=('res', lambda s: (s == 'done').sum())).reset_index()
print(y.groupby('key').agg(games=('game', 'size'), starts_med=('starts', 'median'), starts_max=('starts', 'max'), done_mean=('done', 'mean')).round(2).to_string())
print('\nexamples (S Prism done, big):')
print(x[(x.grp == 'S') & (x.res == 'done')].sort_values('bag', ascending=False).head(6)[['key', 'game', 'r', 'bag', 'dur', 'score', 'escore', 'wins', 'n8', 'closest']].to_string())
print('\nexamples (S Prism stunned / locked / killed):')
print(x[(x.grp == 'S') & x.res.isin(['stunned', 'locked', 'killed'])].head(8)[['key', 'game', 'r', 'bag', 'dur', 'score', 'escore', 'res', 'stopR', 'n8', 'closest']].to_string())
