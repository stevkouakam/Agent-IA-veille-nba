"""LangGraph nodes for the detection pipeline.

Each node is a plain function `(state) -> dict` returning only the keys
it updates — that keeps every node testable in isolation, without
compiling or running the graph. `detect_changes` and `persist` each own
a short-lived DB session rather than sharing one, so a read-only check
can be tested independently of the write path.
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.orm import Session

from agent_ia_veille_nba.agents.state import GameChange, PipelineState
from agent_ia_veille_nba.config import get_watched_teams
from agent_ia_veille_nba.db.repository import get_by_game_id, upsert_game
from agent_ia_veille_nba.db.session import get_session
from agent_ia_veille_nba.nba_data.scoreboard import (
    GameStatus,
    GameUpdate,
    fetch_scoreboard,
    parse_scoreboard,
)
from agent_ia_veille_nba.notifications.telegram import (
    format_change_message,
    send_telegram_message,
)

logger = logging.getLogger(__name__)

# Status transitions worth waking someone up for. Score deltas while a
# game is LIVE are still persisted every cycle (see persist_node) but not
# notified — otherwise every basket would trigger a notification.
NOTIFIABLE_TRANSITIONS = {
    (GameStatus.SCHEDULED, GameStatus.LIVE),
    (GameStatus.LIVE, GameStatus.FINAL),
}


def fetch_scoreboard_node(state: PipelineState) -> dict:
    return {"raw_scoreboard": fetch_scoreboard()}


def parse_node(state: PipelineState) -> dict:
    raw = state["raw_scoreboard"]
    game_date = dt.date.fromisoformat(raw["scoreboard"]["gameDate"])
    updates = parse_scoreboard(raw)

    watched = get_watched_teams()
    if watched is not None:
        updates = [
            update
            for update in updates
            if update.home_team in watched or update.away_team in watched
        ]

    return {"game_date": game_date, "updates": updates}


def detect_changes(session: Session, updates: list[GameUpdate]) -> list[GameChange]:
    """Compare each update to its last known state, in isolation from
    session lifecycle — the piece worth unit testing directly."""
    changes: list[GameChange] = []
    for update in updates:
        previous = get_by_game_id(session, update.game_id)
        previous_status = previous.status if previous is not None else None
        if (previous_status, update.status) in NOTIFIABLE_TRANSITIONS:
            changes.append(
                GameChange(
                    game_id=update.game_id,
                    home_team=update.home_team,
                    away_team=update.away_team,
                    previous_status=previous_status,
                    new_status=update.status,
                    home_score=update.home_score,
                    away_score=update.away_score,
                )
            )
    return changes


def persist_games(
    session: Session, updates: list[GameUpdate], game_date: dt.date
) -> None:
    for update in updates:
        upsert_game(session, update, game_date)


def detect_changes_node(state: PipelineState) -> dict:
    session = get_session()
    try:
        changes = detect_changes(session, state["updates"])
    finally:
        session.close()
    return {"changes": changes}


def persist_node(state: PipelineState) -> dict:
    session = get_session()
    try:
        persist_games(session, state["updates"], state["game_date"])
        session.commit()
    finally:
        session.close()
    return {}


def notify_node(state: PipelineState) -> dict:
    for change in state["changes"]:
        message = format_change_message(change)
        logger.info("sending telegram notification: %s", message)
        send_telegram_message(message)
    return {}


def has_changes(state: PipelineState) -> str:
    """Routing function for the conditional edge after `persist`."""
    return "notify" if state["changes"] else "end"
