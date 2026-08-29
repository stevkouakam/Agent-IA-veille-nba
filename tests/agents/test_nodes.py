import datetime as dt
import json
from pathlib import Path

from agent_ia_veille_nba.agents.nodes import (
    detect_changes,
    has_changes,
    parse_node,
    persist_games,
)
from agent_ia_veille_nba.db.repository import get_by_game_id, upsert_game
from agent_ia_veille_nba.nba_data.scoreboard import (
    GameStatus,
    GameUpdate,
    parse_scoreboard,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "scoreboard_sample.json"
)
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


# --- detect_changes -----------------------------------------------------


def test_detect_changes_flags_scheduled_to_live_transition(db_session):
    upsert_game(db_session, make_update(status=GameStatus.SCHEDULED), GAME_DATE)
    db_session.flush()

    changes = detect_changes(db_session, [make_update(status=GameStatus.LIVE)])

    assert len(changes) == 1
    assert changes[0].previous_status is GameStatus.SCHEDULED
    assert changes[0].new_status is GameStatus.LIVE


def test_detect_changes_flags_live_to_final_transition(db_session):
    upsert_game(db_session, make_update(status=GameStatus.LIVE), GAME_DATE)
    db_session.flush()

    changes = detect_changes(
        db_session, [make_update(status=GameStatus.FINAL, status_text="Final")]
    )

    assert len(changes) == 1
    assert changes[0].new_status is GameStatus.FINAL


def test_detect_changes_ignores_score_change_while_live(db_session):
    upsert_game(
        db_session, make_update(status=GameStatus.LIVE, home_score=10), GAME_DATE
    )
    db_session.flush()

    changes = detect_changes(
        db_session, [make_update(status=GameStatus.LIVE, home_score=20)]
    )

    assert changes == []


def test_detect_changes_ignores_first_sighting_of_a_game(db_session):
    changes = detect_changes(db_session, [make_update(status=GameStatus.SCHEDULED)])
    assert changes == []


# --- persist_games --------------------------------------------------------


def test_persist_games_upserts_every_update(db_session):
    persist_games(db_session, [make_update(home_score=42)], GAME_DATE)
    db_session.flush()

    saved = get_by_game_id(db_session, "0022500999")
    assert saved is not None
    assert saved.home_score == 42


# --- has_changes ------------------------------------------------------------


def test_has_changes_routes_to_notify_when_there_are_changes():
    assert has_changes({"changes": [object()]}) == "notify"


def test_has_changes_routes_to_end_when_empty():
    assert has_changes({"changes": []}) == "end"


# --- sanity check that the fixture from step 2 still parses as expected ----


def test_fixture_scoreboard_still_parses_into_three_updates():
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(parse_scoreboard(raw)) == 3


# --- parse_node -------------------------------------------------------------


def test_parse_node_extracts_game_date_and_all_updates_when_unfiltered(monkeypatch):
    monkeypatch.delenv("WATCHED_TEAMS", raising=False)
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    result = parse_node({"raw_scoreboard": raw})

    assert result["game_date"] == dt.date(2026, 1, 15)
    assert len(result["updates"]) == 3


def test_parse_node_filters_by_watched_teams(monkeypatch):
    monkeypatch.setenv("WATCHED_TEAMS", "LAL")
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    result = parse_node({"raw_scoreboard": raw})

    assert [u.game_id for u in result["updates"]] == ["0022500602"]
