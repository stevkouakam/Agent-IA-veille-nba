"""Email notification channel (Resend), for the non-urgent digest.

Kept separate from the routing logic in agents/ on purpose, same
rationale as notifications/telegram.py: the graph decides *what* goes
in the digest (agents/routing.py), this module decides *how* to
deliver it (message formatting, the Resend API call).
"""

import html
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
    # Titles and links come from external RSS feeds — escape before
    # embedding in HTML so a stray `<`, `&`, or `"` in one can't break
    # the markup or the href attribute.
    title = html.escape(h.headline.title)
    link = html.escape(h.headline.link, quote=True)
    return (
        f"<li><strong>[{h.headline.source}] {h.category.value.upper()}</strong>"
        f"{h.teams_suffix()} &mdash; {h.credibility_score:.0%} credibility<br>"
        f'<a href="{link}">{title}</a></li>'
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
            # `.get(key, default)` alone isn't enough: GitHub Actions sets
            # this env var to "" (not absent) when the repo variable is
            # left unset, which `.get` treats as present.
            "from": os.environ.get("RESEND_FROM_EMAIL") or DEFAULT_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )
