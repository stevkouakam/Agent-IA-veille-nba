"""Small config helpers, sourced from environment variables."""

import os


def get_watched_teams() -> set[str] | None:
    """Tricodes of teams to filter for, or None to watch every team.

    Configured via WATCHED_TEAMS, a comma-separated list (e.g. "BOS,NYK").
    A plain env var is enough for a single-user project — no need for a
    preferences table/UI until there's more than one user to serve.
    """
    raw = os.environ.get("WATCHED_TEAMS", "").strip()
    if not raw:
        return None
    return {team.strip().upper() for team in raw.split(",") if team.strip()}
