"""Fetch and parse NBA headlines (trade rumors + news) from RSS feeds.

Fetch (network I/O) stays separate from parse (pure function), same
rationale as nba_data/scoreboard.py: parsing is unit tested against a
fixed fixture, without hitting the network.

Feeds mix general news outlets (ESPN, CBS Sports) with rumor-heavy ones
(ClutchPoints, Sportando) — every entry is treated the same way for now.
Telling a confirmed trade apart from a rumor by its content is the
classification agent's job (see README roadmap), not this module's.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "espn": "https://www.espn.com/espn/rss/nba/news",
    "cbs_sports": "https://www.cbssports.com/rss/headlines/nba/",
    "clutchpoints": "https://www.clutchpoints.com/nba/feed",
    "sportando": "https://www.sportando.basketball/feed/",
}


@dataclass(frozen=True)
class HeadlineUpdate:
    headline_id: str
    source: str
    title: str
    link: str
    summary: str
    published_at: dt.datetime | None


def fetch_feed(url: str) -> bytes:
    """Download one RSS feed's raw bytes.

    A plain requests User-Agent gets blocked by some of these outlets
    (Cloudflare/bot-detection) — a browser-like one doesn't.
    """
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; nba-watch-bot/1.0)"},
        timeout=15,
    )
    response.raise_for_status()
    return response.content


def fetch_all_feeds() -> dict[str, bytes]:
    """Download every configured feed, keyed by source name.

    One feed failing (timeout, transient block, outage) shouldn't sink
    the whole cycle — log and skip it, keep the rest. Fetched
    concurrently: fully independent HTTP calls, and each already has a
    15s timeout — running them sequentially would let one slow feed add
    up to that same 15s to every other feed's worst case.
    """
    raw: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=len(RSS_FEEDS)) as pool:
        futures = {
            source: pool.submit(fetch_feed, url) for source, url in RSS_FEEDS.items()
        }
        for source, future in futures.items():
            try:
                raw[source] = future.result()
            except requests.RequestException:
                logger.warning("failed to fetch %s feed", source, exc_info=True)
    return raw


def parse_feeds(raw: dict[str, bytes]) -> list[HeadlineUpdate]:
    """Turn raw feed bytes per source into a flat list of HeadlineUpdate."""
    headlines = []
    for source, content in raw.items():
        parsed = feedparser.parse(content)
        for entry in parsed.entries:
            headlines.append(_parse_entry(source, entry))
    return headlines


def _parse_entry(source: str, entry: Any) -> HeadlineUpdate:
    link = entry.get("link", "")
    guid = entry.get("id") or link
    # Feed guids/links have no fixed length or charset — hash down to a
    # stable, DB-friendly key rather than constraining the raw value.
    headline_id = hashlib.sha256(guid.encode("utf-8")).hexdigest()[:32]

    return HeadlineUpdate(
        headline_id=headline_id,
        source=source,
        title=entry.get("title", ""),
        link=link,
        summary=entry.get("summary", ""),
        published_at=_parse_published(entry.get("published")),
    )


def _parse_published(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
