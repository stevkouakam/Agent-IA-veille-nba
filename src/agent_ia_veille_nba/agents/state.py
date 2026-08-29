"""Shared state schema for the detection pipeline graph."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, TypedDict

from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, GameUpdate


@dataclass(frozen=True)
class GameChange:
    """A status transition worth notifying someone about."""

    game_id: str
    home_team: str
    away_team: str
    previous_status: GameStatus | None
    new_status: GameStatus
    home_score: int
    away_score: int


class PipelineState(TypedDict, total=False):
    """State threaded through the graph. Each node sets a subset of keys.

    total=False because the state is built up incrementally — a node
    only needs to return the keys it's responsible for.
    """

    raw_scoreboard: dict[str, Any]
    game_date: dt.date
    updates: list[GameUpdate]
    changes: list[GameChange]
