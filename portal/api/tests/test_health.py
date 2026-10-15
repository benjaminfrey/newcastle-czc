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
