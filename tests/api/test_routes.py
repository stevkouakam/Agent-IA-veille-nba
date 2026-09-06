import datetime as dt
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_ia_veille_nba.api.app import create_app
from agent_ia_veille_nba.api.dependencies import get_db
from agent_ia_veille_nba.db.repository import upsert_game
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, GameUpdate

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "scoreboard_sample.json"
)
LIVE_GAME_ID = "15900602"  # must match FIXTURE_LIVE_GAME_ID in tests/conftest.py


@pytest.fixture
def client(db_session) -> TestClient:
    """A TestClient whose /games route reads from the rolled-back
    db_session fixture instead of opening a real connection."""

    def override_get_db():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_games_returns_seeded_rows(client, db_session):
    upsert_game(
        db_session,
        GameUpdate(
            game_id="0099900001",
            home_team="BOS",
            away_team="NYK",
            home_score=10,
            away_score=8,
            status=GameStatus.LIVE,
            status_text="Q1 5:00",
            period=1,
            game_clock="PT05M00.00S",
        ),
        dt.date(2026, 1, 15),
    )
    db_session.flush()

    response = client.get("/games", params={"game_date": "2026-01-15"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["game_id"] == "0099900001"
    assert body[0]["status"] == "LIVE"


def test_get_games_filters_out_other_dates(client, db_session):
    upsert_game(
        db_session,
        GameUpdate(
            game_id="0099900002",
            home_team="BOS",
            away_team="NYK",
            home_score=0,
            away_score=0,
            status=GameStatus.SCHEDULED,
            status_text="7:30 pm ET",
            period=0,
            game_clock="",
        ),
        dt.date(2026, 1, 15),
    )
    db_session.flush()

    response = client.get("/games", params={"game_date": "2026-02-01"})

    assert response.status_code == 200
    assert response.json() == []


def test_run_cycle_returns_detected_transitions(monkeypatch, seeded_previous_state):
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.fetch_scoreboard", lambda game_date: raw
    )
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.send_telegram_message", lambda text: None
    )
    monkeypatch.delenv("WATCHED_TEAMS", raising=False)

    client = TestClient(create_app())
    response = client.post("/run-cycle")

    assert response.status_code == 200
    body = response.json()
    assert body["updates_count"] == 3
    assert len(body["changes"]) == 1
    change = body["changes"][0]
    assert change["game_id"] == LIVE_GAME_ID
    assert change["previous_status"] == "SCHEDULED"
    assert change["new_status"] == "LIVE"
