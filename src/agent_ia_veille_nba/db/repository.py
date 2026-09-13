"""Read/write helpers for the `games` table.

Deliberately thin: this module knows how to persist a GameUpdate, not
whether that update is worth notifying about — that decision belongs to
the detection agent (step 4), which will call `get_by_game_id` *before*
`upsert_game` to compare old vs. new state.
"""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_ia_veille_nba.db.models import Game, Headline
from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate
from agent_ia_veille_nba.nba_data.scoreboard import GameUpdate


def get_by_game_id(session: Session, game_id: str) -> Game | None:
    return session.scalar(select(Game).where(Game.game_id == game_id))


def list_games(session: Session, game_date: dt.date | None = None) -> list[Game]:
    """All known games, optionally filtered to a single date."""
    stmt = select(Game).order_by(Game.game_date, Game.game_id)
    if game_date is not None:
        stmt = stmt.where(Game.game_date == game_date)
    return list(session.scalars(stmt))


def upsert_game(session: Session, update: GameUpdate, game_date: dt.date) -> Game:
    """Insert a new game row, or update the existing one in place."""
    game = get_by_game_id(session, update.game_id)
    if game is None:
        game = Game(game_id=update.game_id, game_date=game_date)
        session.add(game)

    game.home_team = update.home_team
    game.away_team = update.away_team
    game.home_score = update.home_score
    game.away_score = update.away_score
    game.status = update.status
    game.status_text = update.status_text
    game.period = update.period
    game.game_clock = update.game_clock

    return game


def get_by_headline_id(session: Session, headline_id: str) -> Headline | None:
    return session.scalar(select(Headline).where(Headline.headline_id == headline_id))


def list_headlines(session: Session) -> list[Headline]:
    stmt = select(Headline).order_by(Headline.created_at.desc())
    return list(session.scalars(stmt))


def insert_headline(
    session: Session,
    update: HeadlineUpdate,
    *,
    category: str = "general",
    teams: list[str] | None = None,
    credibility_score: float = 0.5,
) -> Headline:
    """Insert a new headline row. Caller is responsible for having
    already checked it's actually new (see detect_new_headlines).

    `category`/`teams`/`credibility_score` are the classification
    agent's output (agents/classification.py) — kept as plain
    parameters here rather than importing that module, so this data
    layer doesn't have to know about the agent layer built on top of it.
    """
    headline = Headline(
        headline_id=update.headline_id,
        source=update.source,
        title=update.title,
        link=update.link,
        summary=update.summary,
        published_at=update.published_at,
        category=category,
        teams=teams or [],
        credibility_score=credibility_score,
    )
    session.add(headline)
    return headline
