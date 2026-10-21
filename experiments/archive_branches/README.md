# Removed branches, kept in full (Oct 21)

On the user's request the repository keeps three branches: `main`, `god-opponent-model-on`, `god-dynamic-draft-on`. The other
branches were removed after their content was saved here (the git proxy refuses tag pushes, so each branch's commits that `main`
does not have are stored as a verified git bundle):

| Removed branch | Head | Saved as | What it held |
|---|---|---|---|
| `god-dynamic-draft-off` | e97aec2 | `god-dynamic-draft-off.bundle`, zip `submissions/history/god_v8_dynamic_draft_off_20261021.zip` (sha256 57ce3d0c…) | the ladder control of the dynamic draft: v8 play with the dynamic-draft code off |
| `god-opponent-model-off` | 434669e | `god-opponent-model-off.bundle`, zip `submissions/history/god_v8_opponent_model_off_20261020.zip` (279247cc…) | the ladder control of the opponent model (v8 play) |
| `god-v10-off` | 791824f | `god-v10-off.bundle` (zip = `submissions/history/god_dynamic_draft_20261021.zip`, dd7a6189…) | the ladder control of GOD v10 (the dynamic draft `_m1p3`) |
| `god-v10-on` | 09da227 | nothing to save: every commit is in `main` (its zip = GOD v10 = `submissions/history/god_v10_20261021.zip`) | |
| `claude/nice-franklin-lgyb4x` | 09da227 | nothing to save: every commit is in `main` | the session branch |

The zip of `god-opponent-model-on` is also copied to `submissions/history/god_opponent_model_on_20261020.zip` (bd493e64…).

Restore a branch: `git fetch experiments/archive_branches/<name>.bundle refs/remotes/origin/<name>:<name>` (needs `main`, which holds
every prerequisite commit), then `git push origin <name>`.
