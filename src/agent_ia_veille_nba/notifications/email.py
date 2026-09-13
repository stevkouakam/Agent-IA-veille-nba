"""Email notification channel (Resend), for the non-urgent digest.

Kept separate from the routing logic in agents/ on purpose, same
rationale as notifications/telegram.py: the graph decides *what* goes
in the digest (agents/routing.py), this module decides *how* to
deliver it (message formatting, the Resend API call).
"""

import os

import resend
from dotenv import load_dotenv

from agent_ia_veille_nba.agents.classification import ClassifiedHeadline

# Load here rather than relying on some other module having already
# done it — this module must work standalone.
load_dotenv()

# Resend's shared sandbox sender: works without verifying a domain, but
# only delivers to the Resend account's own address. Fine for a
# single-user project; a verified domain would lift that restriction.
DEFAULT_FROM = "NBA Watch <onboarding@resend.dev>"


def _format_row(h: ClassifiedHeadline) -> str:
    teams = f" ({', '.join(h.teams)})" if h.teams else ""
    return (
        f"<li><strong>[{h.headline.source}] {h.category.value.upper()}</strong>"
        f"{teams} &mdash; {h.credibility_score:.0%} credibility<br>"
        f'<a href="{h.headline.link}">{h.headline.title}</a></li>'
    )


def format_digest_email(headlines: list[ClassifiedHeadline]) -> tuple[str, str]:
    """Returns (subject, html_body)."""
    subject = f"NBA Watch digest: {len(headlines)} update(s)"
    html = "<ul>" + "\n".join(_format_row(h) for h in headlines) + "</ul>"
    return subject, html


def send_digest_email(headlines: list[ClassifiedHeadline]) -> None:
    """Send every headline in `headlines` as a single digest email.

    Caller is responsible for only calling this with a non-empty list —
    this module doesn't decide whether there's anything worth sending.
    """
    resend.api_key = os.environ["RESEND_API_KEY"]
    to = os.environ["DIGEST_EMAIL_TO"]
    subject, html = format_digest_email(headlines)

    resend.Emails.send(
        {
            "from": os.environ.get("RESEND_FROM_EMAIL", DEFAULT_FROM),
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )
