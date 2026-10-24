"""Twin of focus.h."""


def kill_value(enemy_bag, bodies, enemy_n, c, p):
	rate = p.team_rate / (enemy_n if enemy_n > 0 else 1)
	return enemy_bag + p.gold_gems * c.kill_gold + bodies * c.respawn_time * rate


def target_priority(kv, rounds_to_kill, p):
	return (1.0 + kv / p.kv_ref) / (1.0 + rounds_to_kill)
