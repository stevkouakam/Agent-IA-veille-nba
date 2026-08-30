"""One-off helper: find your Telegram chat_id from a bot token.

Usage:
    1. Message your bot on Telegram first (Telegram won't let a bot
       message you until you've messaged it at least once).
    2. Put TELEGRAM_BOT_TOKEN in your .env, then run:
           uv run python scripts/get_telegram_chat_id.py
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your .env first.")

    response = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates", timeout=15
    )
    response.raise_for_status()
    updates = response.json().get("result", [])

    if not updates:
        raise SystemExit(
            "No messages found. Open a chat with your bot on Telegram, "
            "send it any message, then run this script again."
        )

    seen: set[int] = set()
    for update in updates:
        chat = update.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        if chat_id is not None and chat_id not in seen:
            seen.add(chat_id)
            print(
                f"chat_id={chat_id}  (from: {chat.get('first_name', chat.get('title', '?'))})"
            )


if __name__ == "__main__":
    main()
