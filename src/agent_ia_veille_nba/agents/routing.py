"""Routes each new headline to Telegram (instant) or the email digest
(batched), based on urgency.

Game status transitions never go through this module: `detect_changes`
(agents/nodes.py) already filters them down to `NOTIFIABLE_TRANSITIONS`
— exactly the "worth waking someone up for" cut — so every `GameChange`
that reaches `notify_node` is Telegram-instant by definition. Headlines
get a real urgency call, since "new" doesn't imply "urgent" for them.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_ia_veille_nba.agents.classification import (
    ClassifiedHeadline,
    HeadlineCategory,
)

# Trade and injury news is what people actually want pushed to them
# right away; signings and general news can wait for the digest.
URGENT_CATEGORIES = {HeadlineCategory.TRADE, HeadlineCategory.INJURY}

# Below this, even trade/injury news isn't confident enough to interrupt
# someone for — it waits for the digest instead.
URGENT_CREDIBILITY_THRESHOLD = 0.8


@dataclass(frozen=True)
class RoutingResult:
    urgent: list[ClassifiedHeadline]
    digest: list[ClassifiedHeadline]


def is_urgent_headline(classified: ClassifiedHeadline) -> bool:
    return (
        classified.category in URGENT_CATEGORIES
        and classified.credibility_score >= URGENT_CREDIBILITY_THRESHOLD
    )


def route_headlines(headlines: list[ClassifiedHeadline]) -> RoutingResult:
    urgent = [h for h in headlines if is_urgent_headline(h)]
    digest = [h for h in headlines if not is_urgent_headline(h)]
    return RoutingResult(urgent=urgent, digest=digest)
