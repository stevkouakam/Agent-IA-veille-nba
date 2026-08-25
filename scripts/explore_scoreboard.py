"""Manual exploration script: fetch and print today's live scoreboard.

Run from your own terminal (not this session) to verify network access:

    uv run python scripts/explore_scoreboard.py
"""

import json

from agent_ia_veille_nba.nba_data.scoreboard import fetch_scoreboard, parse_scoreboard

if __name__ == "__main__":
    raw = fetch_scoreboard()
    print(json.dumps(raw, indent=2)[:2000])
    print("---")
    for game in parse_scoreboard(raw):
        print(game)
