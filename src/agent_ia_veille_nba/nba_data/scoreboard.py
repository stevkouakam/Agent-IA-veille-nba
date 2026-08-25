"""Fetch and parse the NBA live scoreboard (nba_api).

Fetch (network I/O) is kept separate from parse (pure function) so the
parsing logic can be unit tested against a fixed JSON fixture without
hitting the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GameStatus(Enum):
    """Mirrors nba_api's numeric gameStatus field."""

    SCHEDULED = 1
    LIVE = 2
    FINAL = 3


@dataclass(frozen=True)
class GameUpdate:
    game_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status: GameStatus
    status_text: str
    period: int
    game_clock: str


def fetch_scoreboard() -> dict[str, Any]:
    """Call the live nba_api scoreboard endpoint and return the raw JSON.

    Network I/O only, no parsing — keep this thin so it never needs its
    own unit tests beyond an integration smoke test.
    """
    from nba_api.live.nba.endpoints import scoreboard

    return scoreboard.ScoreBoard().get_dict()


def parse_scoreboard(raw: dict[str, Any]) -> list[GameUpdate]:
    """Turn a raw scoreboard payload into a list of GameUpdate records."""
    games = raw.get("scoreboard", {}).get("games", [])
    return [_parse_game(game) for game in games]


def _parse_game(game: dict[str, Any]) -> GameUpdate:
    home = game["homeTeam"]
    away = game["awayTeam"]
    return GameUpdate(
        game_id=game["gameId"],
        home_team=home["teamTricode"],
        away_team=away["teamTricode"],
        home_score=home["score"],
        away_score=away["score"],
        status=GameStatus(game["gameStatus"]),
        status_text=game["gameStatusText"],
        period=game["period"],
        game_clock=game["gameClock"],
    )
