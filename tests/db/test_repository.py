import datetime as dt

from agent_ia_veille_nba.db.models import Game
from agent_ia_veille_nba.db.repository import get_by_game_id, upsert_game
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, GameUpdate

GAME_DATE = dt.date(2026, 1, 15)


def make_update(**overrides: object) -> GameUpdate:
    defaults: dict = {
        "game_id": "0022500999",
        "home_team": "BOS",
        "away_team": "NYK",
        "home_score": 10,
        "away_score": 8,
        "status": GameStatus.LIVE,
        "status_text": "Q1 5:00",
        "period": 1,
        "game_clock": "PT05M00.00S",
    }
    defaults.update(overrides)
    return GameUpdate(**defaults)


def test_upsert_game_inserts_new_row(db_session):
    game = upsert_game(db_session, make_update(), GAME_DATE)
    db_session.flush()

    assert game.id is not None
    fetched = get_by_game_id(db_session, "0022500999")
    assert fetched is not None
    assert fetched.home_score == 10
    assert fetched.status is GameStatus.LIVE


def test_upsert_game_updates_existing_row_in_place(db_session):
    upsert_game(db_session, make_update(), GAME_DATE)
    db_session.flush()

    upsert_game(
        db_session,
        make_update(home_score=20, status=GameStatus.FINAL, status_text="Final"),
        GAME_DATE,
    )
    db_session.flush()

    rows = db_session.query(Game).filter_by(game_id="0022500999").all()
    assert len(rows) == 1
    assert rows[0].home_score == 20
    assert rows[0].status is GameStatus.FINAL


def test_get_by_game_id_returns_none_when_missing(db_session):
    assert get_by_game_id(db_session, "does-not-exist") is None
