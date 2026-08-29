"""End-to-end test: compile the graph and run it against a stubbed fetch
and the real (dockerized) test Postgres.

Unlike the other DB tests, this one can't use the rolled-back `db_session`
fixture — the nodes open their own session via `get_session()`, bound to
the same engine as the running app. So it commits for real and cleans up
explicitly afterwards.
"""

import datetime as dt
import json
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from agent_ia_veille_nba.agents.graph import build_graph
from agent_ia_veille_nba.db.models import Game
from agent_ia_veille_nba.db.repository import upsert_game
from agent_ia_veille_nba.db.session import get_session
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, GameUpdate

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "scoreboard_sample.json"
)
LIVE_GAME_ID = "0022500602"  # LAL vs MIA in the fixture, gameStatus=2 (LIVE)


@pytest.fixture
def seeded_previous_state():
    """Simulate 'last cycle': the LIVE game hadn't started yet."""
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
                game_id=LIVE_GAME_ID,
                home_team="LAL",
                away_team="MIA",
                home_score=0,
                away_score=0,
                status=GameStatus.SCHEDULED,
                status_text="7:00 pm ET",
                period=0,
                game_clock="",
            ),
            game_date=dt.date(2026, 1, 15),
        )
        session.commit()
        yield
    finally:
        for game_id in ("0022500601", "0022500602", "0022500603"):
            session.query(Game).filter_by(game_id=game_id).delete()
        session.commit()
        session.close()


def test_graph_detects_the_scheduled_to_live_transition(
    monkeypatch, seeded_previous_state
):
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.fetch_scoreboard", lambda: raw
    )
    monkeypatch.delenv("WATCHED_TEAMS", raising=False)

    graph = build_graph()
    final_state = graph.invoke({})

    changed_ids = {c.game_id for c in final_state["changes"]}
    assert changed_ids == {LIVE_GAME_ID}
    assert final_state["changes"][0].previous_status is GameStatus.SCHEDULED
    assert final_state["changes"][0].new_status is GameStatus.LIVE
