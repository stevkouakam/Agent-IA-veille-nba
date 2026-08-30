from agent_ia_veille_nba.agents.state import GameChange
from agent_ia_veille_nba.nba_data.scoreboard import GameStatus
from agent_ia_veille_nba.notifications import telegram as telegram_module


def make_change(**overrides: object) -> GameChange:
    defaults: dict = {
        "game_id": "0022500602",
        "home_team": "LAL",
        "away_team": "MIA",
        "previous_status": GameStatus.SCHEDULED,
        "new_status": GameStatus.LIVE,
        "home_score": 0,
        "away_score": 0,
    }
    defaults.update(overrides)
    return GameChange(**defaults)


def test_format_change_message_for_tipoff():
    message = telegram_module.format_change_message(make_change())

    assert "MIA" in message
    assert "LAL" in message
    assert "tips off" in message


def test_format_change_message_for_final_score():
    change = make_change(
        previous_status=GameStatus.LIVE,
        new_status=GameStatus.FINAL,
        home_score=110,
        away_score=104,
    )

    message = telegram_module.format_change_message(change)

    assert "Final" in message
    assert "104" in message
    assert "110" in message


def test_send_telegram_message_calls_bot_with_configured_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    calls = []

    class FakeBot:
        def __init__(self, token):
            calls.append(("init", token))

        async def send_message(self, chat_id, text):
            calls.append(("send", chat_id, text))

    monkeypatch.setattr(telegram_module, "Bot", FakeBot)

    telegram_module.send_telegram_message("hello")

    assert calls == [("init", "fake-token"), ("send", "42", "hello")]
