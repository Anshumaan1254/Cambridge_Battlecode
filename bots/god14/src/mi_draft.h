// mi_draft.h: draft memory version 2 written by GOD's draft (tools/mapintel, docs/DRAFT_MEMORY.md; the reference order is
// tools/mapintel/cpp/test2/main.cpp). GOD's own pick comes first on every draft turn; mapintel's work and the blocks then run under
// the fuel guard. A map too large for the first turn's fuel left gets no image (the champions then play GOD v10's game).
#pragma once

// Every draft turn (P.mi_dmem): call mi_draft_begin() before the pick and mi_draft_after_pick(pick) after it (pick = the champion_draft
// id just picked, -1 if none).
void mi_draft_begin();
void mi_draft_after_pick(int pick);

// P.mi_pick: mapintel's map work before the first pick, so the strong teams' pick prior can weigh in (mi_prior). Returns whether the
// prior is ready.
bool mi_draft_prepare();
// The prior's term for champion_draft id c: ln(rate + 0.05) minus its mean over the 12 picks (0 when not ready).
double mi_prior(int c);
