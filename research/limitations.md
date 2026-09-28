# Known limitations of this build

Honest accounting, per the product spec's own requirement that every
discovery disclose its limitations. This is a Phase 1-5 vertical slice, not
the complete product.

## Data

- **No personnel groupings.** nflverse's public play-by-play release doesn't
  include offense/defense personnel data. Every play's `offense_personnel` /
  `defense_personnel` field is null. The Personnel Dependency Engine and
  Player Absence Engine (spec Sections 13-14) are not implemented against
  invented data -- they're deferred until a data source that actually has
  this is wired in.
- **Two seasons ingested by default** (2022-2023 regular + postseason).
  Change-point and cross-season "appeared this season but not last" analyses
  are only as strong as this window; a team's "before" segment in the
  committed demo data may itself be short.
- **SportsDataIO is untested against a live key.** The adapter
  (`app/providers/sportsdataio/`) is real, working code -- retries, rate
  limiting, response caching, loose schema validation -- but has not been
  exercised against an actual subscription, since none is available in this
  environment. Field names for less-common endpoints (injuries, depth
  charts, snap counts) are not yet mapped into the normalized Play schema.

## Scope not yet built (spec Phases 6-10)

- Sequence Lab, Team Digital Profile, Player Intelligence, and Counterfactual
  Lab pages are not in the frontend nav. Sequence *mining* itself runs (it
  feeds Discovery Feed cards); the dedicated interactive Lab UI for filtering
  and browsing sequences by team/opponent/field-position is future work.
- No natural-language query interface. The product spec is explicit that the
  LLM must never be the analytics engine (Section 21) -- building it before
  the structured-query planner and verified execution path exist would
  produce exactly the "LLM makes up football analysis" pattern the spec
  forbids.
- No GPU acceleration benchmarking (Section 31) -- CPU-only clustering and
  permutation testing is fast enough at this data scale (~100K plays) that a
  GPU path hasn't been justified by a measured bottleneck.
- No computer-vision interfaces (Section 32) -- out of scope until video
  becomes an actual data source.

## Statistical

- Discoveries are associational. Every discovery's `limitations` field says
  so, and the language throughout (title, description) avoids "causes" /
  "guarantees" in favor of "associated with" / "historically" -- but this is
  worth restating plainly: nothing here is a controlled experiment.
- A single flagged anomalous team-week may reflect game script (a blowout
  forcing more passing in the second half) rather than a deliberate scheme
  change. The `limitations` text on anomaly discoveries says this explicitly.
- Change-point detection reports the single largest breakpoint per team per
  run (via `ruptures.Pelt`), not a full multi-regime segmentation.
- Sequence-motif p-values are computed over overlapping sliding windows
  within the same drives, which are not fully independent observations of
  each other -- disclosed in the discovery's own limitations text.
