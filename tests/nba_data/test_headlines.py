import datetime as dt
from pathlib import Path

import requests

from agent_ia_veille_nba.nba_data.headlines import (
    RSS_FEEDS,
    fetch_all_feeds,
    parse_feeds,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "headlines_sample.xml"
)


def raw_feed() -> dict[str, bytes]:
    return {"example_source": FIXTURE_PATH.read_bytes()}


def test_parse_feeds_returns_one_headline_per_entry():
    headlines = parse_feeds(raw_feed())
    assert len(headlines) == 2


def test_parse_feeds_extracts_fields():
    headlines = parse_feeds(raw_feed())
    trade_rumor = headlines[0]

    assert trade_rumor.source == "example_source"
    assert trade_rumor.title == "Team A exploring trade for star guard"
    assert trade_rumor.link == "https://example.com/nba/trade-rumor-1"
    assert "early stages" in trade_rumor.summary
    assert trade_rumor.published_at == dt.datetime(2026, 9, 13, 14, 30, tzinfo=dt.UTC)


def test_parse_feeds_derives_a_stable_headline_id_from_the_guid():
    first_pass = parse_feeds(raw_feed())
    second_pass = parse_feeds(raw_feed())

    assert first_pass[0].headline_id == second_pass[0].headline_id
    assert first_pass[0].headline_id != first_pass[1].headline_id


def test_parse_feeds_handles_no_entries():
    assert parse_feeds({"empty_source": b"<rss><channel></channel></rss>"}) == []


def test_parse_feeds_combines_multiple_sources():
    raw = {"source_a": FIXTURE_PATH.read_bytes(), "source_b": FIXTURE_PATH.read_bytes()}
    headlines = parse_feeds(raw)

    assert len(headlines) == 4
    assert {h.source for h in headlines} == {"source_a", "source_b"}


# --- fetch_all_feeds -----------------------------------------------------


def test_fetch_all_feeds_skips_a_failing_feed_but_keeps_the_rest(monkeypatch):
    sources = list(RSS_FEEDS)

    def fake_fetch(url: str) -> bytes:
        if url == RSS_FEEDS[sources[0]]:
            raise requests.RequestException("boom")
        return b"<rss><channel></channel></rss>"

    monkeypatch.setattr("agent_ia_veille_nba.nba_data.headlines.fetch_feed", fake_fetch)

    raw = fetch_all_feeds()

    assert sources[0] not in raw
    assert set(raw) == set(sources[1:])
