"""Engine and session factory, configured from the DATABASE_URL env var."""

import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg2://nba:nba@localhost:5432/nba_watch"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_database_url())


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    """Return a new session. Caller is responsible for closing it.

    Exposed as a plain function (rather than only the sessionmaker) so it
    can later be swapped for a FastAPI dependency (`Depends(get_session)`)
    without changing call sites.
    """
    return SessionLocal()
