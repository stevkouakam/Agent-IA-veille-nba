# Copy lockfile + pyproject first and sync deps before copying the rest
# of the source — Docker only re-runs `uv sync` when dependencies
# actually change, not on every code edit.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

# The venv baked above is final — without this, `uv run` re-syncs at
# every container start and silently pulls the dev dependency group
# back in, undoing the --no-dev above (and hitting the network for no
# reason on every restart).
ENV UV_NO_SYNC=1

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "agent_ia_veille_nba.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
