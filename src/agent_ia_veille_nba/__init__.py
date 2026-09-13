"""Entry point for running one pipeline cycle.

Used both by `uv run agent-ia-veille-nba` locally and by the scheduled
GitHub Actions workflow (.github/workflows/scheduled-run.yml).
"""

import logging

from agent_ia_veille_nba.agents.graph import build_graph


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    final_state = build_graph().invoke({})
    updates = final_state.get("updates", [])
    changes = final_state.get("changes", [])
    headlines = final_state.get("headlines", [])
    new_headlines = final_state.get("new_headlines", [])

    logger.info(
        "cycle complete: %d game updates (%d changes notified), "
        "%d headlines fetched (%d new, notified)",
        len(updates),
        len(changes),
        len(headlines),
        len(new_headlines),
    )
