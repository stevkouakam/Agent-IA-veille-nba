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

from agent_ia_veille_nba.agents.classification import (
    ClassifiedHeadline,
    classify_headlines,
)
from agent_ia_veille_nba.agents.routing import route_headlines
from agent_ia_veille_nba.agents.state import GameChange, PipelineState
from agent_ia_veille_nba.config import get_watched_teams
from agent_ia_veille_nba.db.repository import (
    get_by_game_id,
    get_by_headline_id,
    insert_headline,
    upsert_game,
)
from agent_ia_veille_nba.db.session import get_session
from agent_ia_veille_nba.nba_data.headlines import fetch_all_feeds, parse_feeds
from agent_ia_veille_nba.nba_data.scoreboard import (
    GameStatus,
    GameUpdate,
    fetch_scoreboard,
    parse_scoreboard,
    today_in_nba_time,
)
from agent_ia_veille_nba.notifications.email import send_digest_email
from agent_ia_veille_nba.notifications.telegram import (
    format_change_message,
    format_headline_message,
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
    # We control the date we ask for, so it's simpler to record it here
    # than to dig it back out of the response in parse_node.
    game_date = today_in_nba_time()
    return {"raw_scoreboard": fetch_scoreboard(game_date), "game_date": game_date}


def parse_node(state: PipelineState) -> dict:
    updates = parse_scoreboard(state["raw_scoreboard"])

    watched = get_watched_teams()
    if watched is not None:
        updates = [
            update
            for update in updates
            if update.home_team in watched or update.away_team in watched
        ]

    return {"updates": updates}


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


def fetch_headlines_node(state: PipelineState) -> dict:
    return {"raw_headlines": fetch_all_feeds()}


def parse_headlines_node(state: PipelineState) -> dict:
    return {"headlines": parse_feeds(state["raw_headlines"])}


def classify_headlines_node(state: PipelineState) -> dict:
    classified = classify_headlines(state["headlines"])

    # Same filtering intent as parse_node's WATCHED_TEAMS check, applied
    # post-classification since teams aren't known until then. A
    # headline mentioning no team at all (general NBA news) still gets
    # through — only ones tied exclusively to unwatched teams are cut.
    watched = get_watched_teams()
    if watched is not None:
        classified = [c for c in classified if not c.teams or set(c.teams) & watched]

    return {"classified_headlines": classified}


def detect_new_headlines(
    session: Session, headlines: list[ClassifiedHeadline]
) -> list[ClassifiedHeadline]:
    """Which of these headlines haven't been seen in a previous cycle —
    the piece worth unit testing directly, same rationale as
    `detect_changes`.

    Also dedupes within this batch itself (by headline_id) — two feeds
    can carry the same syndicated story with the same guid/link in the
    same cycle, and persisting both would violate the table's unique
    constraint on headline_id.
    """
    new = []
    seen_ids: set[str] = set()
    for c in headlines:
        if c.headline.headline_id in seen_ids:
            continue
        if get_by_headline_id(session, c.headline.headline_id) is None:
            new.append(c)
            seen_ids.add(c.headline.headline_id)
    return new


def persist_new_headlines(
    session: Session, headlines: list[ClassifiedHeadline]
) -> None:
    for classified in headlines:
        insert_headline(
            session,
            classified.headline,
            category=classified.category.value,
            teams=list(classified.teams),
            credibility_score=classified.credibility_score,
        )


def detect_new_headlines_node(state: PipelineState) -> dict:
    session = get_session()
    try:
        new_headlines = detect_new_headlines(session, state["classified_headlines"])
    finally:
        session.close()
    return {"new_headlines": new_headlines}


def persist_headlines_node(state: PipelineState) -> dict:
    session = get_session()
    try:
        persist_new_headlines(session, state["new_headlines"])
        session.commit()
    finally:
        session.close()
    return {}


def join_branches_node(state: PipelineState) -> dict:
    """No-op merge point where the scoreboard and headlines branches
    (each fetch -> parse -> detect -> persist) converge before deciding
    whether there's anything worth notifying about."""
    return {}


def notify_node(state: PipelineState) -> dict:
    # Each send below is wrapped individually: these are three
    # independent channels/items, and one failing (bad token, a
    # transient network error, a rate limit) shouldn't stop the
    # others from going out.
    for change in state["changes"]:
        message = format_change_message(change)
        logger.info("sending telegram notification: %s", message)
        try:
            send_telegram_message(message)
        except Exception:
            logger.exception(
                "failed to send telegram notification for game %s", change.game_id
            )

    routing = route_headlines(state.get("new_headlines", []))

    for headline in routing.urgent:
        message = format_headline_message(headline)
        logger.info("sending telegram notification: %s", message)
        try:
            send_telegram_message(message)
        except Exception:
            logger.exception(
                "failed to send telegram notification for headline %s",
                headline.headline.headline_id,
            )

    if routing.digest:
        logger.info("sending email digest: %d headline(s)", len(routing.digest))
        try:
            send_digest_email(routing.digest)
        except Exception:
            logger.exception("failed to send email digest")

    return {}


def has_changes(state: PipelineState) -> str:
    """Routing function for the conditional edge after `join_branches`."""
    changes = state.get("changes", [])
    new_headlines = state.get("new_headlines", [])
    return "notify" if (changes or new_headlines) else "end"
