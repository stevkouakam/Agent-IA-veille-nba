import datetime as dt
from pathlib import Path

from agent_ia_veille_nba.nba_data.headlines import parse_feeds

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
