import datetime as dt
import json
from pathlib import Path

from agent_ia_veille_nba.agents.classification import (
    ClassifiedHeadline,
    HeadlineCategory,
)
from agent_ia_veille_nba.agents.nodes import (
    detect_changes,
    detect_new_headlines,
    has_changes,
    notify_node,
    parse_node,
    persist_games,
    persist_new_headlines,
)
from agent_ia_veille_nba.agents.state import GameChange
from agent_ia_veille_nba.db.repository import (
    get_by_game_id,
    get_by_headline_id,
    upsert_game,
)
from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate
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


def make_headline(**overrides: object) -> HeadlineUpdate:
    defaults: dict = {
        "headline_id": "abc123",
        "source": "espn",
        "title": "Team A exploring trade for star guard",
        "link": "https://example.com/nba/trade-rumor-1",
        "summary": "Sources say discussions are in early stages.",
        "published_at": None,
    }
    defaults.update(overrides)
    return HeadlineUpdate(**defaults)


def make_classified_headline(
    *,
    headline: HeadlineUpdate | None = None,
    category: HeadlineCategory = HeadlineCategory.GENERAL,
    teams: tuple[str, ...] = (),
    credibility_score: float = 0.5,
) -> ClassifiedHeadline:
    return ClassifiedHeadline(
        headline=headline or make_headline(),
        category=category,
        teams=teams,
        credibility_score=credibility_score,
    )


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


# --- detect_new_headlines / persist_new_headlines --------------------------


def test_detect_new_headlines_flags_a_headline_never_seen_before(db_session):
    changes = detect_new_headlines(db_session, [make_classified_headline()])
    assert [c.headline.headline_id for c in changes] == ["abc123"]


def test_detect_new_headlines_ignores_a_headline_already_persisted(db_session):
    persist_new_headlines(db_session, [make_classified_headline()])
    db_session.flush()

    changes = detect_new_headlines(db_session, [make_classified_headline()])

    assert changes == []


def test_persist_new_headlines_inserts_every_headline(db_session):
    persist_new_headlines(
        db_session,
        [
            make_classified_headline(
                category=HeadlineCategory.TRADE,
                teams=("BOS",),
                credibility_score=0.9,
            )
        ],
    )
    db_session.flush()

    saved = get_by_headline_id(db_session, "abc123")
    assert saved is not None
    assert saved.title == "Team A exploring trade for star guard"
    assert saved.category == "trade"
    assert saved.teams == ["BOS"]
    assert saved.credibility_score == 0.9


# --- has_changes ------------------------------------------------------------


def test_has_changes_routes_to_notify_when_there_are_game_changes():
    assert has_changes({"changes": [object()], "new_headlines": []}) == "notify"


def test_has_changes_routes_to_notify_when_there_are_new_headlines():
    assert has_changes({"changes": [], "new_headlines": [object()]}) == "notify"


def test_has_changes_routes_to_end_when_empty():
    assert has_changes({"changes": [], "new_headlines": []}) == "end"


# --- sanity check that the fixture from step 2 still parses as expected ----


def test_fixture_scoreboard_still_parses_into_three_updates():
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(parse_scoreboard(raw)) == 3


# --- parse_node -------------------------------------------------------------


def test_parse_node_returns_all_updates_when_unfiltered(monkeypatch):
    monkeypatch.delenv("WATCHED_TEAMS", raising=False)
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    result = parse_node({"raw_scoreboard": raw})

    assert len(result["updates"]) == 3


def test_parse_node_filters_by_watched_teams(monkeypatch):
    monkeypatch.setenv("WATCHED_TEAMS", "LAL")
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    result = parse_node({"raw_scoreboard": raw})

    assert [u.game_id for u in result["updates"]] == ["15900602"]


# --- notify_node --------------------------------------------------------


def test_notify_node_sends_one_message_per_change(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.send_telegram_message", sent.append
    )

    change = GameChange(
        game_id="0022500602",
        home_team="LAL",
        away_team="MIA",
        previous_status=GameStatus.SCHEDULED,
        new_status=GameStatus.LIVE,
        home_score=0,
        away_score=0,
    )

    notify_node({"changes": [change]})

    assert len(sent) == 1
    assert "MIA" in sent[0] and "LAL" in sent[0]


def test_notify_node_sends_one_message_per_new_headline(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.send_telegram_message", sent.append
    )

    notify_node({"changes": [], "new_headlines": [make_classified_headline()]})

    assert len(sent) == 1
    assert "Team A exploring trade for star guard" in sent[0]
