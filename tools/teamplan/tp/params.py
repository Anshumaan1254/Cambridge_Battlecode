"""Twin of params.h: the versioned parameter set (labels and sources are in the header)."""
from dataclasses import dataclass, fields

VERSION = 1


@dataclass
class Params:
	enhanced_extra: float = 1.0
	enhanced_stun: float = 1.0
	missing_hp_avg: float = 0.5
	hits_taken: float = 1.0
	splash_targets: float = 1.0
	area_targets: float = 1.0
	fight_rounds: float = 8.0
	ranged_front: float = 0.5
	immune_ehp: float = 0.15
	dash_escape: float = 0.2
	reach_escape: float = 0.05
	gold_gems: float = 0.167
	team_rate: float = 0.94
	hazard: float = 0.0016
	danger_hazard: float = 0.02
	items_half: float = 0.0
	capture_mode: int = 1
	bag_fight: int = 30
	bag_fight_scale: float = 60.0
	hunt_bag: float = 25.0
	hunt_bonus: float = 0.5
	kv_ref: float = 40.0
	tb_period: int = 25
	tb_enter: int = 150
	tb_leave: int = 50
	tb_min_round: int = 600
	tb_defer_cap: int = 60
	tb_safe_dist: int = 9
	tb_final_margin: int = 30
	tb_denial_rounds: int = 60
	own_bonus: float = 0.25
	gemfree_front: float = 0.5
	swap_period: int = 50
	swap_hold: int = 150
	swap_margin: float = 0.25
	lag_ratio: float = 0.6


def names():
	"""Field names in header order (the test bot prints the C++ values in this order)."""
	return [f.name for f in fields(Params)]
