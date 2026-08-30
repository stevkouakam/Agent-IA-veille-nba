"""Pydantic response models — the HTTP-facing shape of our domain objects.

Kept separate from the ORM models (db/models.py) and the pipeline's own
dataclasses (agents/state.py) on purpose: what we persist and what we
return over the API are allowed to diverge without one forcing a change
in the other. Built via explicit `from_*` classmethods rather than
Pydantic's `from_attributes`, because both source types store status as
a GameStatus enum, not the string this API exposes.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from agent_ia_veille_nba.agents.state import GameChange
from agent_ia_veille_nba.db.models import Game


class GameOut(BaseModel):
    game_id: str
    game_date: dt.date
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status: str
    status_text: str
    period: int
    game_clock: str
    updated_at: dt.datetime

    @classmethod
    def from_model(cls, game: Game) -> GameOut:
        return cls(
            game_id=game.game_id,
            game_date=game.game_date,
            home_team=game.home_team,
            away_team=game.away_team,
            home_score=game.home_score,
            away_score=game.away_score,
            status=game.status.name,
            status_text=game.status_text,
            period=game.period,
            game_clock=game.game_clock,
            updated_at=game.updated_at,
        )


class GameChangeOut(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    previous_status: str | None
    new_status: str
    home_score: int
    away_score: int

    @classmethod
    def from_domain(cls, change: GameChange) -> GameChangeOut:
        return cls(
            game_id=change.game_id,
            home_team=change.home_team,
            away_team=change.away_team,
            previous_status=(
                change.previous_status.name if change.previous_status else None
            ),
            new_status=change.new_status.name,
            home_score=change.home_score,
            away_score=change.away_score,
        )


class RunCycleOut(BaseModel):
    updates_count: int
    changes: list[GameChangeOut]
