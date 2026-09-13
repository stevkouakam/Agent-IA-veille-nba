"""Classification + verification for NBA headlines.

Tags each headline with the teams it mentions and a coarse category
(trade / injury / signing / general), and assigns a credibility score
combining static source reliability with cross-source corroboration
within the same cycle. This is the nearest approximation of
"verification" reachable without an LLM or a second scrape pass — a
keyword/heuristic pass, not a fact-check. It's deliberately honest
about that rather than pretending to more precision than it has.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from agent_ia_veille_nba.nba_data.headlines import HeadlineUpdate


class HeadlineCategory(Enum):
    TRADE = "trade"
    INJURY = "injury"
    SIGNING = "signing"
    GENERAL = "general"


@dataclass(frozen=True)
class ClassifiedHeadline:
    headline: HeadlineUpdate
    category: HeadlineCategory
    teams: tuple[str, ...]
    credibility_score: float


# Editorial outlets with fact-checking standards score higher than
# aggregator/rumor blogs. Static for now; a longer track record of
# "rumor panned out vs. didn't" per source would make this adaptive,
# but that data doesn't exist yet.
SOURCE_RELIABILITY: dict[str, float] = {
    "espn": 0.9,
    "cbs_sports": 0.85,
    "clutchpoints": 0.6,
    "sportando": 0.6,
}
DEFAULT_RELIABILITY = 0.5

# Two independent outlets running near-identical headlines in the same
# cycle is the closest thing to corroboration available without an
# LLM — bump the score for every headline in such a cluster.
CORROBORATION_BONUS = 0.15
TITLE_SIMILARITY_THRESHOLD = 0.6

_TRADE_KEYWORDS = ("trade", "traded", "trading", "swap", "acquire")
_INJURY_KEYWORDS = (
    "injury",
    "injured",
    "surgery",
    "sprain",
    "strain",
    "questionable",
    "ruled out",
    "tear",
    "fracture",
    "mri",
)
_SIGNING_KEYWORDS = (
    "sign",
    "signs",
    "signed",
    "signing",
    "agrees to",
    "agreed to",
    "extension",
    "free agent",
    "re-sign",
)

# City/nickname aliases -> tricode. Matched as whole words against the
# headline's title+summary. A handful of nicknames (Magic, Heat, Jazz,
# Kings, Thunder) are also common English words — an unrelated mention
# ("Magic Johnson", a weather headline) can false-positive a team tag.
# Acceptable for a heuristic first pass; a real NLP/NER step would fix
# it properly.
TEAM_ALIASES: dict[str, str] = {
    "hawks": "ATL",
    "atlanta": "ATL",
    "celtics": "BOS",
    "boston": "BOS",
    "nets": "BKN",
    "brooklyn": "BKN",
    "hornets": "CHA",
    "charlotte": "CHA",
    "bulls": "CHI",
    "chicago": "CHI",
    "cavaliers": "CLE",
    "cavs": "CLE",
    "cleveland": "CLE",
    "mavericks": "DAL",
    "mavs": "DAL",
    "dallas": "DAL",
    "nuggets": "DEN",
    "denver": "DEN",
    "pistons": "DET",
    "detroit": "DET",
    "warriors": "GSW",
    "golden state": "GSW",
    "rockets": "HOU",
    "houston": "HOU",
    "pacers": "IND",
    "indiana": "IND",
    "clippers": "LAC",
    "lakers": "LAL",
    "grizzlies": "MEM",
    "memphis": "MEM",
    "heat": "MIA",
    "miami": "MIA",
    "bucks": "MIL",
    "milwaukee": "MIL",
    "timberwolves": "MIN",
    "wolves": "MIN",
    "minnesota": "MIN",
    "pelicans": "NOP",
    "new orleans": "NOP",
    "knicks": "NYK",
    "thunder": "OKC",
    "oklahoma city": "OKC",
    "magic": "ORL",
    "orlando": "ORL",
    "76ers": "PHI",
    "sixers": "PHI",
    "philadelphia": "PHI",
    "suns": "PHX",
    "phoenix": "PHX",
    "trail blazers": "POR",
    "blazers": "POR",
    "portland": "POR",
    "kings": "SAC",
    "sacramento": "SAC",
    "spurs": "SAS",
    "san antonio": "SAS",
    "raptors": "TOR",
    "toronto": "TOR",
    "jazz": "UTA",
    "utah": "UTA",
    "wizards": "WAS",
    "washington": "WAS",
}


def classify_category(text: str) -> HeadlineCategory:
    lowered = text.lower()
    if any(keyword in lowered for keyword in _TRADE_KEYWORDS):
        return HeadlineCategory.TRADE
    if any(keyword in lowered for keyword in _INJURY_KEYWORDS):
        return HeadlineCategory.INJURY
    if any(keyword in lowered for keyword in _SIGNING_KEYWORDS):
        return HeadlineCategory.SIGNING
    return HeadlineCategory.GENERAL


def extract_teams(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    tricodes = {
        tricode
        for alias, tricode in TEAM_ALIASES.items()
        if re.search(rf"\b{re.escape(alias)}\b", lowered)
    }
    return tuple(sorted(tricodes))


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def classify_headlines(headlines: list[HeadlineUpdate]) -> list[ClassifiedHeadline]:
    """Tag every headline with a category, its teams, and a credibility
    score — corroboration is checked against the rest of *this* batch
    only, so it only ever reflects same-cycle cross-source agreement."""
    classified = []
    for headline in headlines:
        text = f"{headline.title} {headline.summary}"
        category = classify_category(text)
        teams = extract_teams(text)

        base_score = SOURCE_RELIABILITY.get(headline.source, DEFAULT_RELIABILITY)
        corroborated = any(
            other.source != headline.source
            and _title_similarity(other.title, headline.title)
            >= TITLE_SIMILARITY_THRESHOLD
            for other in headlines
        )
        score = min(
            1.0, base_score + CORROBORATION_BONUS if corroborated else base_score
        )

        classified.append(
            ClassifiedHeadline(
                headline=headline,
                category=category,
                teams=teams,
                credibility_score=score,
            )
        )
    return classified
