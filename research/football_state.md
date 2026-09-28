# Football State representation

## Why not Player / Team / Game / Statistic

GRIDSTATE's fundamental object is the **Football State**: the observable
context immediately before a play, decoupled from what actually happened on
that play. Everything downstream (the state graph, unsupervised clustering,
anomaly/change-point/sequence detection) operates on this separation.

## State vs. Action vs. Outcome

A state must never contain information that is only known *because* of the
play call or its result -- otherwise "trailing teams pass more" would be
built into the input rather than discovered as a finding. Concretely:

**State** (`app/features/state_engine.py::STATE_FEATURE_COLUMNS`):

| Feature | Source column | Notes |
|---|---|---|
| `down` | `down` | 1-4 |
| `ydstogo` | `ydstogo` | yards to convert |
| `yardline_100` | `yardline_100` | distance to opponent's end zone |
| `score_differential` | `score_differential` | posteam perspective |
| `qtr` | `qtr` | 1-4, 5 = OT |
| `game_seconds_remaining` | `game_seconds_remaining` | |
| `play_num_in_drive` | derived | position within the current drive |
| `prev_is_pass` / `prev_is_run` | derived from `prev_play_type` | previous play in the same drive, grouped by `(game_id, drive)` |
| `prev2_is_pass` / `prev2_is_run` | derived from `prev_play_type_2` | two plays back |

**Action / Outcome** (`app/features/state_engine.py::OUTCOME_COLUMNS`), measured
*conditional on* a state, never folded into it: `play_type`, `pass_play`,
`rush_play`, `shotgun`, `no_huddle`, `complete_pass`, `touchdown`,
`first_down`, `interception`, `fumble_lost`, `epa`.

Shotgun/no-huddle are formation and tempo decisions made at the same time as
the play call -- they are measured as part of a state's outcome profile
(e.g. `shotgun_rate`), not used to define the state itself.

## Deterministic state key vs. unsupervised discovery

Two different granularities use this same underlying separation:

- **State graph** (`app/graph/state_graph.py`): a small, interpretable,
  deterministic key -- `down|distance_bucket|field_zone|score_bucket|qtr` --
  used for transition probabilities and graph centrality. Buckets:
  - distance: `short_1_3`, `medium_4_6`, `long_7_9`, `very_long_10plus`
  - field zone (yardline_100 = distance to opponent goal): `inside_10`,
    `red_zone` (10-20), `opponent_territory` (20-40), `midfield` (40-60),
    `own_territory` (60-80), `backed_up` (80-100)
  - score: `trailing_big` (<=-9), `trailing`, `tied`, `leading`,
    `leading_big` (>=9)
- **Unsupervised discovery** (`app/discovery/clustering.py`): the full
  continuous `STATE_FEATURE_COLUMNS` vector, standardized and clustered
  without the hand-picked buckets above, so the engine can find structure the
  deterministic buckets don't assume.

## What's missing, honestly

nflverse's public play-by-play release does **not** include offense/defense
personnel groupings (`offense_personnel` / `defense_personnel` are declared
nullable on the `Play` model and always null for nflverse-sourced data in
this slice). That data lives in a separate NGS-derived participation dataset
this vertical slice does not ingest. The Personnel Dependency Engine (Section
13-14 of the product spec) is deferred until that data source is wired in --
it is not implemented against invented fields.
