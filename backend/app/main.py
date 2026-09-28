from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import discoveries, evidence, games, ingest, plays, players, states, system, teams
from app.config import settings
from app.core.logging import configure_logging
from app.db import init_db

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GRIDSTATE API",
    description="Autonomous NFL Data Discovery & Tactical Intelligence Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": settings.mode.value}


app.include_router(system.router)
app.include_router(games.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(plays.router)
app.include_router(states.router)
app.include_router(discoveries.router)
app.include_router(evidence.router)
app.include_router(ingest.router)
