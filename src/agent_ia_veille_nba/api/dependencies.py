"""FastAPI dependencies."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from agent_ia_veille_nba.db.session import get_session


def get_db() -> Iterator[Session]:
    """Yield a session for the duration of one request, then close it."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
