# GRIDSTATE

**Autonomous NFL Data Discovery & Tactical Intelligence Engine.**

> Don't query the game. Discover it.

GRIDSTATE ingests real NFL play-by-play data, builds a Football State
representation for every play, and runs an unsupervised discovery
engine — clustering, anomaly detection, change-point detection, sequence
motif mining — that surfaces statistically validated patterns nobody
explicitly asked it to find. Every discovery traces back to exact games and
plays; nothing is fabricated, hard-coded, or presented as an "AI insight"
without the underlying statistics.

This is a **Phase 1-5 vertical slice** of the full product spec: ingestion,
the Football State engine, the state graph, the discovery engine, and the
evidence engine are real and complete. See [`research/limitations.md`](research/limitations.md)
for exactly what's deferred (Sequence Lab / Team & Player profile pages /
Counterfactual Lab UI / natural-language interface) and why.

## Modes

GRIDSTATE never breaks and never fakes live data:

| Mode | When | Data source |
|---|---|---|
| **LIVE** | `SPORTSDATAIO_API_KEY` is set | SportsDataIO API (`backend/app/providers/sportsdataio/`) |
| **LOCAL** | No key, but `backend/data/raw/pbp_<season>.parquet` exists | Full nflverse season(s) you've downloaded |
| **DEMO** | No key, no local download | The committed trimmed nflverse sample in `backend/data/sample/` |

The current mode is always shown in the frontend's nav bar and via `GET
/system`. DEMO data is real nflverse play-by-play (2022 + 2023 seasons,
trimmed to the columns the pipeline uses) — not synthetic — so discoveries
you see out of the box are genuine, just computed over a smaller window than
a full multi-season LIVE ingestion would use.

## Quickstart

**WSL / Linux / macOS / git-bash:**
```bash
make demo
# or directly: bash scripts/demo.sh
```

**Native Windows PowerShell:**
```powershell
.\scripts\demo.ps1
```

Either script: creates a Python virtualenv, installs backend dependencies,
runs the full ingestion → state graph → discovery engine pipeline against the
committed sample data, then starts the API (`http://localhost:8000`) and the
frontend dev server (`http://localhost:5173`).

To use a real SportsDataIO key instead, copy `.env.example` to `.env` and set
`SPORTSDATAIO_API_KEY` before running.

## Manual setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # .venv/bin/python on POSIX
.venv/Scripts/python.exe scripts/run_pipeline.py 2022 2023
.venv/Scripts/python.exe -m uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev
```

To pull additional/newer seasons instead of relying on the committed sample:
```bash
.venv/Scripts/python.exe -c "from app.providers.nflverse.client import download_season; download_season(2024)"
.venv/Scripts/python.exe scripts/run_pipeline.py 2022 2023 2024
```

## Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q
```

31 tests cover: nflverse column normalization (including a regression guard
for a real bug caught during development — `prev_play_type` leaking across
games that share a drive number), Football State bucket derivation, state
graph transition-probability correctness, the full statistical validation
battery (Benjamini-Hochberg against a known reference, bootstrap CI coverage,
permutation test power), discovery→evidence→exact-play lineage round trips,
clustering smoke tests, and FastAPI endpoint smoke tests.

## Architecture

```
SportsDataIO API  ──┐
                     ├──> Ingestion ──> Raw store ──> Normalization
nflverse parquet  ──┘                                      │
                                                            v
                                                   Football State Engine
                                                            │
                                  ┌─────────────────────────┼─────────────────────────┐
                                  v                         v                         v
                            State Graph            Discovery Engine            (Sequence mining
                       (deterministic states,   (unsupervised clustering,       runs inside the
                        real transition probs,   anomaly/changepoint/motif       Discovery Engine)
                        entropy, centrality)      detection, all bootstrap/
                                                   permutation/BH-validated)
                                  │                         │
                                  └───────────┬─────────────┘
                                              v
                                     Evidence Engine (traces every
                                     discovery to exact games/plays)
                                              │
                                              v
                                      FastAPI ──> React/TypeScript UI
```

Backend: FastAPI, SQLAlchemy + SQLite (application data: games, plays,
discoveries, evidence), Polars + Parquet (raw/normalized play data), DuckDB
path reserved for larger-than-memory analytical queries, scikit-learn +
ruptures + statsmodels + NetworkX (the actual discovery algorithms).

Frontend: React 19 + TypeScript + Vite, no UI component library — a
purpose-built ledger/terminal design (see design rationale inline in
`frontend/src/styles/`) rather than generic dashboard cards.

## API

```
GET  /health
GET  /system                              counts, versions, current mode
GET  /games            ?season&week&team
GET  /teams
GET  /players          ?role=passer|rusher|receiver
GET  /plays             ?game_id&team&season&week&play_type
GET  /states            ?down&min_sample_size        deterministic state-graph nodes
GET  /states/{id}
GET  /states/{id}/transitions
GET  /states/discovered                    unsupervised clusters
GET  /states/discovered/{id}
GET  /discoveries       ?discovery_type&team
GET  /discoveries/{id}
GET  /discoveries/{id}/evidence
POST /discoveries/run                      "Find something I didn't ask" — re-runs the engine now
GET  /evidence/{id}
POST /ingest             {seasons, download}
```

## Security

`SPORTSDATAIO_API_KEY` is read server-side only (`backend/app/config.py`) and
is never referenced anywhere under `frontend/`. Never commit `.env`.

## Research

See [`research/`](research/) for the Football State methodology, the full
statistical validation writeup (effect sizes, bootstrap/permutation
procedures, Benjamini-Hochberg correction, stability measures), and known
limitations.
