from fastapi import FastAPI

from portal_api.config import Settings
from portal_api.db import make_engine
from portal_api.routes import health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Newcastle Applicant Portal", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.include_router(health.router)
    return app
