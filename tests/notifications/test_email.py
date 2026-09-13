from agent_ia_veille_nba.agents.classification import (
    ClassifiedHeadline,
    HeadlineCategory,
)
from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate
from agent_ia_veille_nba.notifications import email as email_module


def make_classified(**overrides: object) -> ClassifiedHeadline:
    headline = HeadlineUpdate(
        headline_id="abc123",
        source="espn",
        title="Rookie wins player of the week",
        link="https://example.com/nba/rookie-award",
        summary="A strong week for the young guard.",
        published_at=None,
    )
    defaults: dict = {
        "headline": headline,
        "category": HeadlineCategory.GENERAL,
        "teams": (),
        "credibility_score": 0.5,
    }
    defaults.update(overrides)
    return ClassifiedHeadline(**defaults)


def test_format_digest_email_includes_every_headline():
    subject, html = email_module.format_digest_email(
        [make_classified(), make_classified()]
    )

    assert "2" in subject
    assert html.count("Rookie wins player of the week") == 2


def test_format_digest_email_includes_teams_when_present():
    _, html = email_module.format_digest_email([make_classified(teams=("BOS", "LAL"))])

    assert "BOS" in html and "LAL" in html


def test_format_digest_email_escapes_html_in_title_and_link():
    malicious = make_classified(
        headline=HeadlineUpdate(
            headline_id="x",
            source="espn",
            title='<script>alert("hi")</script>',
            link='https://example.com/"><b>x</b>',
            summary="",
            published_at=None,
        )
    )

    _, html = email_module.format_digest_email([malicious])

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert '"><b>' not in html


def test_send_digest_email_calls_resend_with_configured_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "fake-key")
    monkeypatch.setenv("DIGEST_EMAIL_TO", "you@example.com")
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)

    calls = []

    class FakeEmails:
        @staticmethod
        def send(params):
            calls.append(params)

    monkeypatch.setattr(email_module.resend, "Emails", FakeEmails)

    email_module.send_digest_email([make_classified()])

    assert len(calls) == 1
    assert calls[0]["to"] == ["you@example.com"]
    assert calls[0]["from"] == email_module.DEFAULT_FROM
    assert "Rookie wins player of the week" in calls[0]["html"]


def test_send_digest_email_falls_back_to_default_when_from_env_is_empty_string(
    monkeypatch,
):
    # GitHub Actions sets this env var to "" (not absent) when the repo
    # variable is left unset — the fallback must treat that as unset too.
    monkeypatch.setenv("RESEND_API_KEY", "fake-key")
    monkeypatch.setenv("DIGEST_EMAIL_TO", "you@example.com")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "")

    calls = []

    class FakeEmails:
        @staticmethod
        def send(params):
            calls.append(params)

    monkeypatch.setattr(email_module.resend, "Emails", FakeEmails)

    email_module.send_digest_email([make_classified()])

    assert calls[0]["from"] == email_module.DEFAULT_FROM
