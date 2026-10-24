"""Twin of bag.h."""


def fight_bar(base, bag, p):
	return base * (1.0 + bag / p.bag_fight_scale)


def bank_before_fight(bag, enemy_dist, enemy_reach, walk_bank, avoidable, p):
	return bool(avoidable) and bag >= p.bag_fight and enemy_dist <= enemy_reach + 3 and walk_bank <= enemy_dist + p.bag_fight // 10


def hunt_bonus(enemy_bag, ours, theirs, p):
	if ours < theirs or enemy_bag < p.hunt_bag:
		return 0.0
	return p.hunt_bonus * enemy_bag / p.hunt_bag


def bank_now_wins(banked, own_bag, allies_bags, c):
	return banked + own_bag + allies_bags >= c.winning_gems
