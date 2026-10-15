"""Shared fixtures. Tests need the dev services running:
    docker compose -f portal/deploy/compose.dev.yml up -d --wait
Each test session builds a fresh database named by PORTAL_TEST_DATABASE_URL."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portal_api.config import Settings
from portal_api.mail import OutboxMailer
from portal_api.main import create_app

API_DIR = Path(__file__).resolve().parent.parent
TEST_URL = os.environ.get(
    "PORTAL_TEST_DATABASE_URL",
    "postgresql+psycopg://portal:portal@localhost:5433/portal_test",
)


def _recreate_database(url: str) -> None:
    base, name = url.rsplit("/", 1)
    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    _recreate_database(TEST_URL)
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")
    eng = create_engine(TEST_URL)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def clean(request):
    yield
    if "engine" in request.fixturenames:
        eng = request.getfixturevalue("engine")
        with eng.begin() as conn:
            conn.execute(text(
                "TRUNCATE applicant, signin_token, session, event RESTART IDENTITY CASCADE"
            ))


@pytest.fixture
def settings():
    return Settings(
        database_url=TEST_URL,
        public_base_url="http://testserver",
        cookie_secure=False,
    )


@pytest.fixture
def outbox():
    return OutboxMailer()


@pytest.fixture
def client(engine, settings, outbox):
    with TestClient(create_app(settings, outbox)) as c:
        yield c
