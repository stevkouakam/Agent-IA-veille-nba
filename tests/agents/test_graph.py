"""End-to-end test: compile the graph and run it against a stubbed fetch
and the real (dockerized) test Postgres.

Uses the `seeded_previous_state` fixture (see tests/conftest.py) rather
than `db_session`: the graph's nodes open their own session against the
same engine, so they can't share a rolled-back transaction with the test.
"""

import json
from pathlib import Path

from agent_ia_veille_nba.agents.graph import build_graph
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "scoreboard_sample.json"
)
LIVE_GAME_ID = "0022500602"  # must match FIXTURE_LIVE_GAME_ID in tests/conftest.py


def test_graph_detects_the_scheduled_to_live_transition(
    monkeypatch, seeded_previous_state
):
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.fetch_scoreboard", lambda: raw
    )
    monkeypatch.setattr(
        "agent_ia_veille_nba.agents.nodes.send_telegram_message", lambda text: None
    )
    monkeypatch.delenv("WATCHED_TEAMS", raising=False)

    graph = build_graph()
    final_state = graph.invoke({})

    changed_ids = {c.game_id for c in final_state["changes"]}
    assert changed_ids == {LIVE_GAME_ID}
    assert final_state["changes"][0].previous_status is GameStatus.SCHEDULED
    assert final_state["changes"][0].new_status is GameStatus.LIVE
