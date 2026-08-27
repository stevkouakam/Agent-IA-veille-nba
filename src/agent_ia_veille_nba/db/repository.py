"""Read/write helpers for the `games` table.

Deliberately thin: this module knows how to persist a GameUpdate, not
whether that update is worth notifying about — that decision belongs to
the detection agent (step 4), which will call `get_by_game_id` *before*
`upsert_game` to compare old vs. new state.
"""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_ia_veille_nba.db.models import Game
from agent_ia_veille_nba.nba_data.scoreboard import GameUpdate


def get_by_game_id(session: Session, game_id: str) -> Game | None:
    return session.scalar(select(Game).where(Game.game_id == game_id))


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
