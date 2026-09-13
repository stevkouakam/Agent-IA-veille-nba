from agent_ia_veille_nba.agents.classification import (
    HeadlineCategory,
    classify_category,
    classify_headlines,
    extract_teams,
)
from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate


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


# --- classify_category ------------------------------------------------------


def test_classify_category_detects_trade():
    assert classify_category("Lakers exploring a trade for a star guard") is (
        HeadlineCategory.TRADE
    )


def test_classify_category_detects_injury():
    assert classify_category("Star forward out for two weeks with ankle sprain") is (
        HeadlineCategory.INJURY
    )


def test_classify_category_detects_signing():
    assert classify_category("Guard agrees to sign with new team") is (
        HeadlineCategory.SIGNING
    )


def test_classify_category_defaults_to_general():
    assert classify_category("Season preview: what to watch tonight") is (
        HeadlineCategory.GENERAL
    )


# --- extract_teams -----------------------------------------------------------


def test_extract_teams_matches_nickname():
    assert extract_teams("Celtics rally in the fourth quarter") == ("BOS",)


def test_extract_teams_matches_city():
    assert extract_teams("Boston pulls off a comeback win") == ("BOS",)


def test_extract_teams_returns_multiple_teams_sorted():
    assert extract_teams("Lakers host the Celtics tonight") == ("BOS", "LAL")


def test_extract_teams_returns_empty_tuple_when_no_team_mentioned():
    assert extract_teams("The league announces new referee guidelines") == ()


def test_extract_teams_does_not_match_substrings():
    # "Jazz" shouldn't fire on unrelated words containing it as a substring.
    assert extract_teams("The jazzy pregame show returns") == ()


# --- classify_headlines -------------------------------------------------------


def test_classify_headlines_scores_known_source_by_its_reliability():
    result = classify_headlines([make_headline(source="espn")])
    assert result[0].credibility_score == 0.9


def test_classify_headlines_uses_default_reliability_for_unknown_source():
    result = classify_headlines([make_headline(source="some_random_blog")])
    assert result[0].credibility_score == 0.5


def test_classify_headlines_boosts_score_for_cross_source_corroboration():
    headlines = [
        make_headline(
            headline_id="a", source="clutchpoints", title="Star guard traded to rival"
        ),
        make_headline(
            headline_id="b", source="sportando", title="Star guard traded to rival"
        ),
    ]

    result = classify_headlines(headlines)

    assert result[0].credibility_score == 0.6 + 0.15
    assert result[1].credibility_score == 0.6 + 0.15


def test_classify_headlines_does_not_boost_unrelated_headlines_from_other_sources():
    headlines = [
        make_headline(
            headline_id="a", source="espn", title="Star guard traded to rival"
        ),
        make_headline(
            headline_id="b", source="cbs_sports", title="Rookie wins player of the week"
        ),
    ]

    result = classify_headlines(headlines)

    assert result[0].credibility_score == 0.9
    assert result[1].credibility_score == 0.85


def test_classify_headlines_attaches_category_and_teams():
    result = classify_headlines(
        [make_headline(title="Celtics explore trade for star guard")]
    )

    assert result[0].category is HeadlineCategory.TRADE
    assert result[0].teams == ("BOS",)
    assert result[0].headline.headline_id == "abc123"
