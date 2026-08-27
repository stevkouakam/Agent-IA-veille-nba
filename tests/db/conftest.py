"""Fixtures for tests hitting the real (dockerized) Postgres.

Each test runs inside a transaction that is rolled back afterwards, so
tests never leave data behind or depend on execution order.
"""

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from agent_ia_veille_nba.db.session import engine


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
