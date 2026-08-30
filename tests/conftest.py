"""Shared fixtures for any test hitting the real (dockerized) Postgres.

`db_session` runs a test inside a transaction that's rolled back
afterwards, so tests never leave data behind. `seeded_previous_state` is
for the handful of tests that instead exercise a full LangGraph run (via
`graph.invoke` or the `/run-cycle` endpoint) — those nodes open their own
sessions against the same engine, bypassing the rollback trick, so that
fixture commits for real and cleans up explicitly in its teardown.
"""

import datetime as dt

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from agent_ia_veille_nba.db.models import Game
from agent_ia_veille_nba.db.repository import upsert_game
from agent_ia_veille_nba.db.session import engine, get_session
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, GameUpdate

# Game ids present in tests/fixtures/scoreboard_sample.json.
FIXTURE_GAME_IDS = ("0022500601", "0022500602", "0022500603")
FIXTURE_LIVE_GAME_ID = "0022500602"  # LAL vs MIA, gameStatus=2 (LIVE) in the fixture
FIXTURE_GAME_DATE = dt.date(2026, 1, 15)


@pytest.fixture
def db_session() -> Session:
    try:
        connection = engine.connect()
    except OperationalError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(
            f"Postgres not reachable ({exc}); run `docker compose up -d db` first"
        )

    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def seeded_previous_state():
    """Simulate 'last cycle': the fixture's LIVE game hadn't started yet."""
    session = get_session()
    try:
        session.connection()
    except OperationalError as exc:  # pragma: no cover - environment-dependent
        session.close()
        pytest.skip(
            f"Postgres not reachable ({exc}); run `docker compose up -d db` first"
        )

    try:
        upsert_game(
            session,
            GameUpdate(
                game_id=FIXTURE_LIVE_GAME_ID,
                home_team="LAL",
                away_team="MIA",
                home_score=0,
                away_score=0,
                status=GameStatus.SCHEDULED,
                status_text="7:00 pm ET",
                period=0,
                game_clock="",
            ),
            game_date=FIXTURE_GAME_DATE,
        )
        session.commit()
        yield
    finally:
        for game_id in FIXTURE_GAME_IDS:
            session.query(Game).filter_by(game_id=game_id).delete()
        session.commit()
        session.close()
