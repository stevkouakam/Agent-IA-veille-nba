"""Telegram notification channel.

Kept separate from the detection logic in agents/ on purpose: the state
graph decides *whether* something is worth notifying (agents/nodes.py),
this module decides *how* to deliver it (message formatting, the
Telegram HTTP call). agents/nodes.py depends on this module, never the
other way around.
"""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot

from agent_ia_veille_nba.agents.state import GameChange
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus

# Load here rather than relying on some other module (e.g. db.session)
# having already done it — this module must work standalone.
load_dotenv()


def format_change_message(change: GameChange) -> str:
    if change.new_status is GameStatus.LIVE:
        return f"🏀 {change.away_team} @ {change.home_team} tips off"
    if change.new_status is GameStatus.FINAL:
        return (
            f"🏁 Final: {change.away_team} {change.away_score} - "
            f"{change.home_score} {change.home_team}"
        )
    return (
        f"{change.away_team} @ {change.home_team}: "
        f"{change.new_status.name} ({change.away_score}-{change.home_score})"
    )


def send_telegram_message(text: str) -> None:
    """Send `text` to the configured chat.

    Uses asyncio.run() because python-telegram-bot is async-only — safe
    here since the whole pipeline (LangGraph nodes, FastAPI routes) runs
    synchronously, so this is never called from inside a running event
    loop.
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    bot = Bot(token=token)
    asyncio.run(bot.send_message(chat_id=chat_id, text=text))
