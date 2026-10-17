#!/usr/bin/env python3
"""Compare fight-outcome predictors on logged combat() evaluations (tools/ml/parse_logs.mjs output).

usage: train.py DATA.csv [DATA.csv ...] [--folds 5] [--targets die,kill] [--with-dec] [--seed 0]

Targets (next 12 rounds): die = this body died, kill = an enemy within 6 died.
Every model is scored out of fold with a game-level split (GroupKFold over games), so no game is in both
the training and the test part. Models:
  formula   the hand-made advantage (adv_f = our time-to-die / their time-to-die x fight_scale), as a score;
            for log-loss it is calibrated with a 1-D logistic fit on log(adv_f) in each training fold
  logreg    L2 logistic regression on standardised features
  tree      CART decision tree (depth 5, >= 100 rows per leaf)
  xgb       gradient-boosted trees (depth 3, 150 rounds, eta 0.05)
  mlp       small neural network (16-8 ReLU, early stopping)
"""
import argparse, math, sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb

# Raw state features from the log (identity and position columns, labels and the decision are excluded).
BASE = ['hp', 'max_hp', 'str', 'focus', 'r_dmg', 'r_cc', 'r_aoe', 'r_reset', 'r_dash', 'can_attack', 'my_burst',
		'allies_near', 'a_hp', 'a_max', 'a_dps', 'backup', 'dead_allies', 'a_alive',
		'nE', 'their_hp', 'their_dps', 'incoming', 'stunners', 'e_max', 'e_min', 'e_reach', 'e_d3', 'e_dash', 'e_ranged', 'e_alive',
		'nearest', 'tgt_hp', 'tgt_max', 'tgt_d', 'tgt_gems', 'tgt_chan', 'e_gems',
		'killable', 'in_reach', 'chaser', 'chaser_dash', 'can_escape', 't_die', 'dh', 'da', 'on_spawn', 'gems', 'gold',
		't_kill_us', 't_kill_them', 'deficit', 'fscale']


def add_derived(df):
	df = df.copy()
	df['hp_frac'] = df.hp / df.max_hp.clip(lower=1)
	df['a_frac'] = np.where(df.a_max > 0, df.a_hp / df.a_max.clip(lower=1), 1.0)
	df['e_frac'] = df.their_hp / df.e_max.clip(lower=1)
	df['log_adv'] = np.log(df.adv_f.clip(lower=1e-3))
	df['hp_ratio'] = np.log((df.hp + df.a_hp + 1) / (df.their_hp + 1))
	df['dps_ratio'] = np.log((df.str + df.a_dps + 1) / (df.their_dps + 1))
	df['our_half'] = (df.dh <= df.da).astype(int)
	df['num_diff'] = df.allies_near + 1 - df.nE
	df['inc_frac'] = df.incoming / df.hp.clip(lower=1)
	df['score_diff'] = df.ours_g - df.theirs_g
	df['rnd'] = df['round']
	return df


DERIVED = ['hp_frac', 'a_frac', 'e_frac', 'log_adv', 'hp_ratio', 'dps_ratio', 'our_half', 'num_diff', 'inc_frac', 'score_diff', 'rnd']


def feature_matrix(df, with_dec):
	cols = BASE + DERIVED
	X = df[cols].astype(float).copy()
	# champion type one-hot (ours and the target's): kits differ a lot
	for t in sorted(df.type.unique()):
		X[f'type_{t}'] = (df.type == t).astype(float)
	for t in sorted(df.tgt_type.unique()):
		X[f'tgt_{t}'] = (df.tgt_type == t).astype(float)
	if with_dec:
		for k in (0, 1, 2, 4):
			X[f'dec_{k}'] = (df.dec == k).astype(float)
	return X


def models(seed):
	return {
		'logreg': lambda: ('scale', LogisticRegression(C=0.5, max_iter=2000)),
		'tree': lambda: ('raw', DecisionTreeClassifier(max_depth=5, min_samples_leaf=100, random_state=seed)),
		'xgb': lambda: ('raw', xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
												min_child_weight=5, reg_lambda=1.0, eval_metric='logloss', random_state=seed, n_jobs=1)),
		'mlp': lambda: ('scale', MLPClassifier(hidden_layer_sizes=(16, 8), alpha=1e-3, early_stopping=True, max_iter=300, random_state=seed)),
	}


def oof(df, X, y, groups, folds, seed):
	"""Out-of-fold probabilities for every model (game-level folds)."""
	pred = {k: np.zeros(len(y)) for k in ['formula'] + list(models(seed))}
	gkf = GroupKFold(n_splits=folds)
	la = df.log_adv.values.reshape(-1, 1)
	for tr, te in gkf.split(X, y, groups):
		# formula: monotone in log(adv); calibrated 1-D logistic for log-loss
		f = LogisticRegression(max_iter=1000).fit(la[tr], y[tr])
		pred['formula'][te] = f.predict_proba(la[te])[:, 1]
		sc = StandardScaler().fit(X.values[tr])
		for name, mk in models(seed).items():
			kind, m = mk()
			Xtr = sc.transform(X.values[tr]) if kind == 'scale' else X.values[tr]
			Xte = sc.transform(X.values[te]) if kind == 'scale' else X.values[te]
			m.fit(Xtr, y[tr])
			pred[name][te] = m.predict_proba(Xte)[:, 1]
	return pred


def game_bootstrap_auc_diff(y, a, b, groups, n=200, seed=0):
	"""95% interval of AUC(a) - AUC(b) resampling whole games."""
	rng = np.random.default_rng(seed)
	g = pd.Series(groups)
	idx_by = {k: np.where(g.values == k)[0] for k in g.unique()}
	keys = list(idx_by)
	diffs = []
	for _ in range(n):
		pick = rng.choice(len(keys), len(keys), replace=True)
		ii = np.concatenate([idx_by[keys[p]] for p in pick])
		if y[ii].min() == y[ii].max():
			continue
		diffs.append(roc_auc_score(y[ii], a[ii]) - roc_auc_score(y[ii], b[ii]))
	return np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('data', nargs='+')
	ap.add_argument('--folds', type=int, default=5)
	ap.add_argument('--targets', default='die,kill')
	ap.add_argument('--with-dec', action='store_true')
	ap.add_argument('--seed', type=int, default=0)
	ap.add_argument('--importance', action='store_true')
	args = ap.parse_args()
	df = pd.concat([pd.read_csv(p) for p in args.data], ignore_index=True)
	df = add_derived(df)
	X = feature_matrix(df, args.with_dec)
	groups = df.game.values
	print(f'{len(df)} rows, {df.game.nunique()} games, {df.groupby(["game", "body", "enc"]).ngroups} encounters, {X.shape[1]} features'
		  f'{" (+ decision)" if args.with_dec else ""}')
	print('decisions:', df.dec.value_counts().sort_index().to_dict(), ' opponents:', df.opp.value_counts().to_dict())
	for t in args.targets.split(','):
		y = df[t].values.astype(int)
		pred = oof(df, X, y, groups, args.folds, args.seed)
		print(f'\n== target {t}: base rate {y.mean():.3f} ({y.sum()} positives)')
		print(f'{"model":10s} {"AUC":>7s} {"logloss":>8s}   AUC - formula (95% game bootstrap)')
		base_ll = log_loss(y, np.full(len(y), y.mean()))
		raw_formula = -df.log_adv.values if t in ('die', 'adie', 'hploss') else df.log_adv.values
		auc_raw = roc_auc_score(y, raw_formula)
		print(f'{"constant":10s} {0.5:7.3f} {base_ll:8.4f}')
		print(f'{"formula":10s} {auc_raw:7.3f} {log_loss(y, np.clip(pred["formula"], 1e-6, 1 - 1e-6)):8.4f}   (raw adv score; log-loss after 1-D calibration)')
		for name in models(args.seed):
			p = np.clip(pred[name], 1e-6, 1 - 1e-6)
			lo, hi = game_bootstrap_auc_diff(y, p, raw_formula, groups, seed=args.seed)
			print(f'{name:10s} {roc_auc_score(y, p):7.3f} {log_loss(y, p):8.4f}   {roc_auc_score(y, p) - auc_raw:+.3f} [{lo:+.3f}, {hi:+.3f}]')
		if args.importance:
			m = xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
								  min_child_weight=5, eval_metric='logloss', random_state=args.seed, n_jobs=1).fit(X.values, y)
			imp = pd.Series(m.get_booster().get_score(importance_type='gain')).rename(lambda k: X.columns[int(k[1:])])
			print('xgb gain importance:', ', '.join(f'{k} {v:.1f}' for k, v in imp.sort_values(ascending=False).head(15).items()))


if __name__ == '__main__':
	main()
