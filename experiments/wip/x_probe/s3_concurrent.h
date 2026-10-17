// SCEN 3: several bodies tribute at the same centre altar in the same round (two of team A, two of team B), with bags of different size:
// A Vendetta 72 (3 gem clusters), A Ryth 22 (wolf), B Vendetta 48 (2 clusters), B Ryth 24 (1 cluster). Everyone starts at TR.
static void scenario() {
	static Carrier cv;
	auto& me = bc::self();
	const auto t = me.champion_name();
	const bool A = is_team_a();
	const unsigned TR = 66;
	bool was = cv.started;
	if (t == bc::champion_type::vendetta) {
		if (A) carrier(cv, { {GEM1, 1}, {GEM3, 1}, {GEM2, 1} }, vec2{11, 11}, TR);
		else carrier(cv, { {mir(GEM1), 1}, {mir(GEM3), 1} }, vec2{13, 13}, TR);
	} else if (t == bc::champion_type::ryth) {
		if (A) carrier(cv, { {WOLF, 1} }, vec2{11, 12}, TR);
		else carrier(cv, { {mir(GEM2), 1} }, vec2{13, 12}, TR);
	} else return;
	if (cv.started || was) { logst("S3"); }
}
