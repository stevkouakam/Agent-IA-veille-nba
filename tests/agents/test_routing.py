from agent_ia_veille_nba.agents.classification import (
    ClassifiedHeadline,
    HeadlineCategory,
)
from agent_ia_veille_nba.agents.routing import is_urgent_headline, route_headlines
from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate


def make_classified(**overrides: object) -> ClassifiedHeadline:
    headline_fields = {
        "headline_id": "abc123",
        "source": "espn",
        "title": "Team A exploring trade for star guard",
        "link": "https://example.com/nba/trade-rumor-1",
        "summary": "Sources say discussions are in early stages.",
        "published_at": None,
    }
    classified_defaults: dict = {
        "category": HeadlineCategory.TRADE,
        "teams": ("BOS",),
        "credibility_score": 0.9,
    }
    for key in list(overrides):
        if key in headline_fields:
            headline_fields[key] = overrides.pop(key)
    classified_defaults.update(overrides)
    return ClassifiedHeadline(
        headline=HeadlineUpdate(**headline_fields), **classified_defaults
    )


# --- is_urgent_headline -------------------------------------------------


def test_is_urgent_for_high_credibility_trade():
    assert is_urgent_headline(
        make_classified(category=HeadlineCategory.TRADE, credibility_score=0.9)
    )


def test_is_urgent_for_high_credibility_injury():
    assert is_urgent_headline(
        make_classified(category=HeadlineCategory.INJURY, credibility_score=0.85)
    )


def test_is_not_urgent_below_credibility_threshold():
    assert not is_urgent_headline(
        make_classified(category=HeadlineCategory.TRADE, credibility_score=0.7)
    )


def test_is_not_urgent_for_signing_category_even_at_high_credibility():
    assert not is_urgent_headline(
        make_classified(category=HeadlineCategory.SIGNING, credibility_score=0.95)
    )


def test_is_not_urgent_for_general_category():
    assert not is_urgent_headline(
        make_classified(category=HeadlineCategory.GENERAL, credibility_score=0.95)
    )


# --- route_headlines -----------------------------------------------------


def test_route_headlines_splits_urgent_and_digest():
    urgent_one = make_classified(
        headline_id="a", category=HeadlineCategory.TRADE, credibility_score=0.9
    )
    digest_one = make_classified(
        headline_id="b", category=HeadlineCategory.GENERAL, credibility_score=0.9
    )

    result = route_headlines([urgent_one, digest_one])

    assert result.urgent == [urgent_one]
    assert result.digest == [digest_one]


def test_route_headlines_handles_empty_input():
    result = route_headlines([])
    assert result.urgent == []
    assert result.digest == []
