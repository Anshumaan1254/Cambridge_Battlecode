"""Twin of timing.h."""


def starting_team(rnd):
	return 0 if rnd % 2 == 1 else 1


def turn_pos(rnd, team, rank, n_team, n_other):
	if team == starting_team(rnd):
		return 2 * rank if rank < n_other else 2 * n_other + (rank - n_other)
	return 2 * rank + 1 if rank < n_other else 2 * n_other + (rank - n_other)


def we_act_first(rnd, team, our_rank, n_ours, e_rank, n_theirs):
	pu = turn_pos(rnd, team, our_rank, n_ours, n_theirs)
	pe = turn_pos(rnd, 1 - team, e_rank, n_theirs, n_ours)
	if pe > pu:
		return False
	return turn_pos(rnd + 1, team, our_rank, n_ours, n_theirs) < turn_pos(rnd + 1, 1 - team, e_rank, n_theirs, n_ours)


def rank_of(prio, ids, me):
	return sum(1 for i in range(len(prio)) if i != me and (prio[i] > prio[me] or (prio[i] == prio[me] and ids[i] < ids[me])))
