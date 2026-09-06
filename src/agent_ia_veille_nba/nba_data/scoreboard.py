"""Fetch and parse NBA game data from balldontlie.io.

Originally built against nba_api's live scoreboard endpoint (see
docs/nba_api_notes.md), but that endpoint turned out to be blocked by
an Akamai-level restriction affecting every network tested against it —
including a plain residential connection, not just cloud/CI IP ranges.
balldontlie.io is unaffected, and its free tier includes live in-game
data (see docs/balldontlie_setup.md).

Fetch (network I/O) stays separate from parse (pure function), same
rationale as before: parsing is unit tested against a fixed fixture,
without hitting the network.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# Load here rather than relying on some other module (e.g. db.session)
# having already done it — this module must work standalone.
load_dotenv()

BASE_URL = "https://api.balldontlie.io/v1/games"

# NBA schedules games by the US Eastern calendar day, not the caller's
# local one — "today" must mean the same thing regardless of which
# timezone the machine running this happens to be in (a GitHub Actions
# runner defaults to UTC, for instance).
_NBA_TZ = ZoneInfo("America/New_York")


def today_in_nba_time() -> dt.date:
    return dt.datetime.now(tz=_NBA_TZ).date()


class GameStatus(Enum):
    """Mirrors balldontlie's `status_state` field.

    Games with any other status_state (postponed, canceled, delayed,
    suspended, abandoned, unknown) are dropped in parse_scoreboard —
    there's nothing meaningful to track for them yet.
    """

    SCHEDULED = "scheduled"
    LIVE = "in_progress"
    FINAL = "final"


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


def fetch_scoreboard(game_date: dt.date | None = None) -> dict[str, Any]:
    """Call balldontlie.io's /games endpoint for `game_date` (default: today)."""
    game_date = game_date or today_in_nba_time()
    api_key = os.environ["BALLDONTLIE_API_KEY"]
    response = requests.get(
        BASE_URL,
        params={"dates[]": game_date.isoformat()},
        headers={"Authorization": api_key},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def parse_scoreboard(raw: dict[str, Any]) -> list[GameUpdate]:
    """Turn a raw /games payload into a list of GameUpdate records."""
    updates = []
    for game in raw.get("data", []):
        try:
            status = GameStatus(game["status_state"])
        except ValueError:
            continue  # postponed/canceled/etc. — nothing to track yet
        updates.append(_parse_game(game, status))
    return updates


def _parse_game(game: dict[str, Any], status: GameStatus) -> GameUpdate:
    return GameUpdate(
        game_id=str(game["id"]),
        home_team=game["home_team"]["abbreviation"],
        away_team=game["visitor_team"]["abbreviation"],
        home_score=game["home_team_score"],
        away_score=game["visitor_team_score"],
        status=status,
        status_text=game["status"],
        period=game["period"],
        game_clock=game.get("time") or "",
    )
