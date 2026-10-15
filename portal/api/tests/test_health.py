from sqlalchemy import text

from portal_api.config import Settings
from portal_api.main import create_app
from fastapi.testclient import TestClient


def test_health_reports_database_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok"}


def test_health_reports_database_down_as_503():
    bad = Settings(database_url="postgresql+psycopg://portal:portal@localhost:1/none")
    with TestClient(create_app(bad)) as c:
        r = c.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": "unavailable"}


def test_postgis_extension_installed(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT extname FROM pg_extension WHERE extname='postgis'")).scalar() == "postgis"


def test_database_connections_are_closed_when_the_app_stops(engine, settings):
    # Every app opens a connection pool; one left open per app exhausted Postgres's
    # 100-connection limit in the test suite (deferred M1 review minor, hit in M2).
    app = create_app(settings)
    with TestClient(app) as c:
        c.get("/api/health")
        assert app.state.engine.pool.checkedin() == 1
    assert app.state.engine.pool.checkedin() == 0
