"""FastAPI application factory.

A factory (rather than a module-level `app = FastAPI()`) so tests can
build a fresh app instance instead of sharing global state.

Run locally with: uvicorn agent_ia_veille_nba.api.app:app --reload
"""

from fastapi import FastAPI

from agent_ia_veille_nba.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="NBA Watch",
        description="Multi-agent NBA monitoring pipeline.",
    )
    app.include_router(router)
    return app


app = create_app()
