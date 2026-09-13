"""API routes.

`run_cycle` reuses the exact same compiled graph the scheduled job
(step 7) will call — the API is one more way to trigger the pipeline,
not a separate implementation of it.
"""

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agent_ia_veille_nba.agents.graph import build_graph
from agent_ia_veille_nba.api.dependencies import get_db
from agent_ia_veille_nba.api.schemas import (
    GameChangeOut,
    GameOut,
    HeadlineOut,
    RunCycleOut,
)
from agent_ia_veille_nba.db.repository import list_games, list_headlines

router = APIRouter()
_graph = build_graph()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/run-cycle", response_model=RunCycleOut)
def run_cycle() -> RunCycleOut:
    final_state = _graph.invoke({})
    return RunCycleOut(
        updates_count=len(final_state["updates"]),
        changes=[GameChangeOut.from_domain(c) for c in final_state["changes"]],
        new_headlines_count=len(final_state["new_headlines"]),
    )


@router.get("/games", response_model=list[GameOut])
def get_games(
    game_date: dt.date | None = None,
    session: Session = Depends(get_db),
) -> list[GameOut]:
    return [GameOut.from_model(g) for g in list_games(session, game_date)]


@router.get("/headlines", response_model=list[HeadlineOut])
def get_headlines(session: Session = Depends(get_db)) -> list[HeadlineOut]:
    return [HeadlineOut.from_model(h) for h in list_headlines(session)]
