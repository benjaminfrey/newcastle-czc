from contextlib import asynccontextmanager

from fastapi import FastAPI

from portal_api.config import Settings
from portal_api.db import make_engine
from portal_api.mail import Mailer, SmtpMailer
from portal_api.ratelimit import SlidingWindow
from portal_api.routes import auth as auth_routes, health, property as property_routes


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    # Close the pool's connections when the app stops.
    app.state.engine.dispose()


def create_app(settings: Settings | None = None, mailer: Mailer | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Newcastle Applicant Portal", docs_url=None, redoc_url=None, lifespan=_lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.lookup_limiter = SlidingWindow(settings.lookup_limit_per_minute)
    app.state.tile_limiter = SlidingWindow(settings.tile_limit_per_minute)
    app.state.mailer = mailer or SmtpMailer(settings.smtp_host, settings.smtp_port, settings.smtp_from)
    app.include_router(health.router)
    app.include_router(auth_routes.router)
    app.include_router(property_routes.router)
    return app
