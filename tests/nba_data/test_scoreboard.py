import json
from pathlib import Path

import pytest

from agent_ia_veille_nba.nba_data.scoreboard import GameStatus, parse_scoreboard

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "scoreboard_sample.json"
)


@pytest.fixture
def raw_scoreboard() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_parse_scoreboard_returns_one_update_per_game(raw_scoreboard):
    games = parse_scoreboard(raw_scoreboard)
    assert len(games) == 3


def test_parse_scoreboard_extracts_scheduled_game(raw_scoreboard):
    games = parse_scoreboard(raw_scoreboard)
    scheduled = games[0]

    assert scheduled.game_id == "0022500601"
    assert scheduled.home_team == "NYK"
    assert scheduled.away_team == "BOS"
    assert scheduled.home_score == 0
    assert scheduled.away_score == 0
    assert scheduled.status is GameStatus.SCHEDULED


def test_parse_scoreboard_extracts_live_game(raw_scoreboard):
    games = parse_scoreboard(raw_scoreboard)
    live = games[1]

    assert live.status is GameStatus.LIVE
    assert live.home_team == "LAL"
    assert live.away_team == "MIA"
    assert live.home_score == 88
    assert live.away_score == 91
    assert live.period == 3
    assert live.status_text == "Q3 05:23"


def test_parse_scoreboard_extracts_final_game(raw_scoreboard):
    games = parse_scoreboard(raw_scoreboard)
    final = games[2]

    assert final.status is GameStatus.FINAL
    assert final.status_text == "Final"
    assert final.home_score == 104
    assert final.away_score == 110


def test_parse_scoreboard_handles_no_games():
    assert parse_scoreboard({"scoreboard": {"games": []}}) == []
