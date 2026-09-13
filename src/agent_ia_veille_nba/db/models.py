"""ORM models — the persisted state the detection agent will diff against."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from agent_ia_veille_nba.db.base import Base
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus


class Game(Base):
    """Latest known state of one NBA game, keyed by balldontlie's game id.

    Each pipeline cycle upserts one row per game in today's scoreboard.
    `updated_at` marks the last time this row was refreshed, and is what
    lets the detection agent tell a genuinely new update apart from an
    unchanged one.
    """

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    game_date: Mapped[dt.date] = mapped_column(Date)

    home_team: Mapped[str] = mapped_column(String(3))
    away_team: Mapped[str] = mapped_column(String(3))
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus, name="game_status"))
    status_text: Mapped[str] = mapped_column(String(50))
    period: Mapped[int] = mapped_column(Integer, default=0)
    game_clock: Mapped[str] = mapped_column(String(20), default="")

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (
            f"Game(game_id={self.game_id!r}, {self.away_team}@{self.home_team}, "
            f"{self.away_score}-{self.home_score}, status={self.status.name})"
        )


class Headline(Base):
    """One RSS entry (trade rumor or news item) we've already seen.

    Headlines are immutable once published — unlike `games`, there's no
    upsert here: a pipeline cycle only ever inserts rows for entries not
    already in this table, which is exactly what "new headline" means.
    """

    __tablename__ = "headlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    headline_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000))
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Headline(source={self.source!r}, title={self.title!r})"
