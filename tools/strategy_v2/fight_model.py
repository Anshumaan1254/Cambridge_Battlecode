#!/usr/bin/env python3
"""How well do simple numbers at the start of a fight predict who loses it? (replay data only)

For every fight found by analyze.py (4+ champion hits), take the state one round before the first hit, the bodies
of each side within 8 tiles of the first hit, and build features:
  lanchester = log((HP_us x DPS_us) / (HP_them x DPS_them))   (what legend's combat() estimates)
  n_diff     = bodies us - bodies them
  first_us   = 1 if our side dealt the first hit
  camps      = awake camps within 3 of our bodies (proxy: our bodies took camp damage in the 3 rounds before)
Label: we lost more bodies than they did in the fight (ties = 0).
Prints the AUC of each feature alone and of a cross-validated logistic regression and a small tree, grouped by match
(no match in both train and test).

usage: python3 -I fight_model.py DMG_DIR ANALYSIS_JSON
"""
import collections
import json
import math
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(__file__))
from analyze import stats_of  # noqa: E402

BEST_MOD = {'Cassi': 2.0, 'Stellar': 2.0, 'Prism': 1.5, 'Tavi': 2.2, 'Ren': 1.25, 'Ryth': 1.0, 'Marcella': 2.0,
            'Willow': 0.0, 'Issac': 0.0, 'Varg': 0.0, 'Vendetta': 0.0, 'VesperVale': 0.0}


def main():
    dmg_dir, ana = sys.argv[1], sys.argv[2]
    A = json.load(open(ana))
    X, y, groups, names = [], [], [], []
    for m in A:
        d = json.load(open(os.path.join(dmg_dir, m['name'] + '.json')))
        bt = {b['index']: (b['team'], b['type']) for b in d['meta']['bodies']}
        st = {(rr['r'], c[0]): c for rr in d['rounds'] for c in rr['ch']}
        camp_hits = collections.defaultdict(float)
        for x in d['dmg']:
            if x[2] == 'm' and x[5] == 'c' and x[7] < 0:
                camp_hits[(x[0], x[6])] += -x[7]
        for e in m['engagements']:
            if e['hits'] < 4:
                continue
            r0 = e['r0']
            hp = [0.0, 0.0]
            dps = [0.0, 0.0]
            n = [0, 0]
            campd = 0.0
            for b, (t, ty) in bt.items():
                s = st.get((r0 - 1, b))
                if not s or not s[7]:
                    continue
                if max(abs(s[3] - e['x']), abs(s[4] - e['y'])) > 8:
                    continue
                _, strv, fo, _, _, _ = stats_of(ty, s[11])
                hp[t] += s[5]
                dps[t] += strv + fo * BEST_MOD.get(ty, 0) / 8.0
                n[t] += 1
                if t == 0:
                    campd += sum(camp_hits.get((rr, b), 0) for rr in range(r0 - 3, r0 + 1))
            if n[0] == 0 or n[1] == 0:
                continue
            lan = math.log(max(1e-6, hp[0] * dps[0]) / max(1e-6, hp[1] * dps[1]))
            X.append([lan, n[0] - n[1], 1.0 if e['first'] == 0 else 0.0, 1.0 if campd > 0 else 0.0])
            y.append(1 if e['deaths0'] > e['deaths1'] else 0)
            groups.append(m['name'])
    X = np.array(X)
    y = np.array(y)
    print(f'fights {len(y)}, we lost more bodies in {y.sum()} ({100 * y.mean():.0f}%)')
    for j, nm in enumerate(['lanchester (stats x health)', 'body difference', 'we hit first', 'we took camp damage']):
        sign = -1 if nm != 'we took camp damage' else 1
        try:
            print(f'  AUC of {nm:28s} alone: {roc_auc_score(y, sign * X[:, j]):.2f}')
        except ValueError:
            pass
    gkf = GroupKFold(n_splits=5)
    for nm, mk in (('logistic regression', lambda: LogisticRegression(max_iter=1000)),
                   ('decision tree depth 3', lambda: DecisionTreeClassifier(max_depth=3, min_samples_leaf=8))):
        pred = np.zeros(len(y))
        for tr, te in gkf.split(X, y, groups):
            clf = mk().fit(X[tr], y[tr])
            pred[te] = clf.predict_proba(X[te])[:, 1]
        print(f'  {nm}: cross-validated AUC {roc_auc_score(y, pred):.2f} (folds grouped by match)')
    clf = LogisticRegression(max_iter=1000).fit(X, y)
    print('  logistic weights [lanchester, body diff, we hit first, camp damage]:', np.round(clf.coef_[0], 2), 'bias', round(float(clf.intercept_[0]), 2))
    # calibration of the lanchester estimate: how often do we lose when we "should" win?
    for lo, hi in ((-9, -0.5), (-0.5, 0), (0, 0.5), (0.5, 9)):
        sel = (X[:, 0] >= lo) & (X[:, 0] < hi)
        if sel.sum():
            print(f'  lanchester in [{lo:+.1f},{hi:+.1f}): fights {sel.sum():3d}, we lost more bodies in {100 * y[sel].mean():.0f}%')


if __name__ == '__main__':
    main()
