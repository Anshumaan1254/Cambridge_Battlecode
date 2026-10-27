// teamplan/timing.h: who acts next between two opposing bodies (TEAMPLAN.md 2 and 4, P4). Measured on a decoded top-team replay:
// champion turns alternate between the teams one body at a time, team A (raw team 0) starts odd rounds and team B even rounds, and
// inside a team higher priority acts first; when one team has fewer bodies left, the other's last bodies act back to back.
// A body's priority for the current round is readable for any champion in sight (cambc::champion::prev_priority()), its own team from
// cambc::detail::sdk_my_team(). Python twin: tools/teamplan/timing.py.
#pragma once

namespace teamplan
{
// Team (0 = A, 1 = B) that starts `round`.
inline int starting_team(int round) { return (round % 2 == 1) ? 0 : 1; }

// Position (0 = first) in the round's turn sequence of the body with rank `rank` (0 = first inside its team) of team `team`, with
// `n_team` and `n_other` bodies taking turns in that round.
inline int turn_pos(int round, int team, int rank, int n_team, int n_other)
{
	(void)n_team;
	if (team == starting_team(round))
		return rank < n_other ? 2 * rank : 2 * n_other + (rank - n_other);
	return rank < n_other ? 2 * rank + 1 : 2 * n_other + (rank - n_other);
}

// We are acting now in `round` (our team `team`, rank `our_rank`, `n_ours` bodies) and consider stepping into the reach of an enemy body
// of rank `e_rank` (`n_theirs` bodies): true if our next action comes before its next one, i.e. it already acted this round and we act
// before it next round. Stepping in otherwise hands it the first hit.
inline bool we_act_first(int round, int team, int our_rank, int n_ours, int e_rank, int n_theirs)
{
	const int pu = turn_pos(round, team, our_rank, n_ours, n_theirs);
	const int pe = turn_pos(round, 1 - team, e_rank, n_theirs, n_ours);
	if (pe > pu)
		return false;
	return turn_pos(round + 1, team, our_rank, n_ours, n_theirs) < turn_pos(round + 1, 1 - team, e_rank, n_theirs, n_ours);
}

// Rank inside a team from the bodies' priorities (higher first; ties by the lower id, measured by test_teamplan.py --turn-order).
inline int rank_of(const int* prio, const int* ids, int n, int me)
{
	int r = 0;
	for (int i = 0; i < n; ++i)
		if (i != me && (prio[i] > prio[me] || (prio[i] == prio[me] && ids[i] < ids[me])))
			++r;
	return r;
}
} // namespace teamplan
