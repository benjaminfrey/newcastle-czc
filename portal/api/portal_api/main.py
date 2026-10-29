from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from portal_api.config import Settings
from portal_api.db import make_engine
from portal_api.mail import Mailer, SmtpMailer
from portal_api.ratelimit import SlidingWindow
from portal_api.scan import ClamdScanner, Scanner
from portal_api.storage import ObjectStore, S3Store
from portal_api.routes import attachments as attachment_routes, auth as auth_routes, forms as form_routes, \
    health, projects as project_routes, property as property_routes, screener as screener_routes


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    # Close the pool's connections when the app stops.
    app.state.engine.dispose()


_PRIVATE = ("/api/projects", "/api/attachments", "/api/me", "/api/auth")


def create_app(settings: Settings | None = None, mailer: Mailer | None = None,
               store: ObjectStore | None = None, scanner: Scanner | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Newcastle Applicant Portal", docs_url=None, redoc_url=None, lifespan=_lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.lookup_limiter = SlidingWindow(settings.lookup_limit_per_minute)
    app.state.tile_limiter = SlidingWindow(settings.tile_limit_per_minute)
    app.state.mailer = mailer or SmtpMailer(settings.smtp_host, settings.smtp_port, settings.smtp_from)
    app.state.store = store or S3Store(settings)
    app.state.scanner = scanner or ClamdScanner(settings.clamd_host, settings.clamd_port)
    @app.middleware("http")
    async def _no_store(request: Request, call_next):
        # Applicants' records are private and change as they type: never let a browser
        # (or a shared library computer) keep a copy or reuse a stale one.
        response = await call_next(request)
        if request.url.path.startswith(_PRIVATE) and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(health.router)
    app.include_router(auth_routes.router)
    app.include_router(property_routes.router)
    app.include_router(screener_routes.router)
    app.include_router(form_routes.router)
    app.include_router(project_routes.router)
    app.include_router(attachment_routes.router)
    return app
