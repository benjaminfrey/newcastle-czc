# Applicant Portal M1 — Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Applicant Portal's foundation: an API with a database, an append-only audit
log, email sign-in links, a React + HeroUI shell, CI, and a deployment on the chair's VM over HTTPS.

**Architecture:** `portal/api` is a FastAPI app using SQLAlchemy Core (plain SQL via `text()`, sync)
against Postgres/PostGIS, migrated by Alembic. `portal/web` is a Vite + React + TypeScript app
styled with Tailwind v4 and HeroUI v3; in development Vite proxies `/api` to the API. Docker
Compose runs Postgres and Mailpit for development and the full stack (Caddy, API, Postgres) on the
VM.

**Tech Stack:** Python 3.14 · FastAPI 0.143.1 · uvicorn 0.54.0 · SQLAlchemy 2.1.4 · psycopg 3.3.6 ·
Alembic 1.20.0 · pydantic-settings 2.16.0 · email-validator 2.3.0 · pytest 9.1.1 · httpx 0.28.1 ·
Node 24 · React 19.3.1 · Vite 8.3.4 · TypeScript 5.9.3 · Tailwind CSS 4.3.3 · @heroui/react 3.2.6 ·
react-router 8.4.0 · Vitest 5.0.4 · Testing Library 16.3.3 · Postgres 17 + PostGIS 3.5 · Mailpit ·
Caddy 2.

**Spec:** `specs/2026-10-14-applicant-portal-design.md` · **Roadmap:**
`plans/2026-10-14-applicant-portal-roadmap.md`

## Global Constraints

- Commit only when the chair has approved execution of this plan; stage files **by name**, never
  `git add -A` / `git add .` (the tree holds untracked material that must not be swept in).
- Every commit message ends with `Co-Authored-By: <the Claude model that wrote it> <noreply@anthropic.com>`.
- Never push, open a PR, or touch the VM without the chair's explicit go-ahead in chat.
- Python for the portal is **3.14** in its own venv at `portal/api/.venv` (the system `python3`
  is 3.15 and is not used). Do not touch `build/permit-review/` or anything outside `portal/`,
  `.github/workflows/portal.yml` and `.gitignore`.
- Sign-in links are **single-use and expire after 15 minutes**; sessions use **secure, HTTP-only
  cookies**; sign-in is **rate-limited**; **no CAPTCHA**.
- No third-party trackers or analytics; nothing an applicant enters goes to any outside service
  except the email relay. **No AI.**
- The `event` log is append-only and hash-chained, using the Board app's formula:
  `hash = sha256(prev_hash || id || at || actor || kind || payload_json)`, no separator, genesis
  `"0" * 64`. Events never carry an email address or other personal detail — ids only.
- Plain language in every applicant-facing string; no Code jargon in the shell.
- No component may depend on a feature only one hosting vendor offers.

## Review Focus

1. **Link prefetchers.** Mail scanners open links in email; a GET that consumed the token would
   sign the scanner in and burn the applicant's link. The token travels in the URL **fragment**
   (`/signin/verify#token=…`) and is redeemed only by a POST from the page — tested in Task 5
   (`test_verify_requires_post`) and Task 6 (`Verify.test.tsx`).
2. **Two clicks on the same link** (double-click, two tabs). The second must fail cleanly with the
   same "link has expired or was already used" message, never a 500 or a second session — Task 5
   `test_link_is_single_use` and `test_concurrent_redeem_succeeds_once`.
3. **Email case and spaces.** `Ben@Example.com ` and `ben@example.com` are one applicant — Task 5
   `test_email_is_normalised`.
4. **Mail relay down.** Requesting a link must answer with a plain "we couldn't send the email" 503,
   not a 500, and leave no usable token behind (the email is sent *before* the token is stored) — Task 5 `test_mail_failure_returns_503_and_no_token`.
5. **Audit log under concurrency.** Two requests appending events at once must not fork the hash
   chain — Task 3 `test_concurrent_appends_keep_one_chain`.

---

## Task 0: Prerequisites (the chair)

Not code. The implementer **stops and reports** if any check fails.

- [ ] **Step 1: A Docker runtime on the Mac.** No Docker is installed today. The chair picks one;
  the free command-line option is:

```bash
brew install colima docker docker-compose
```

```bash
colima start --cpu 2 --memory 4
```

Check: `docker info` prints a Server section.

- [ ] **Step 2: Python 3.14 present.** Check: `/opt/homebrew/bin/python3.14 --version` prints
  `Python 3.14.x` (it does as of 2026-10-14).

- [ ] **Step 3 (needed only for Task 8): VM details.** Host name or IP, SSH user, and the host name
  the portal will answer on (an interim name is fine — spec O7). The VM needs Docker Engine with the
  Compose plugin, and ports 80/443 open.

---

## Task 1: API skeleton, dev services, health check

**Files:**
- Create: `portal/README.md`
- Create: `portal/deploy/compose.dev.yml`
- Create: `portal/api/requirements.txt`, `portal/api/requirements-dev.txt`
- Create: `portal/api/portal_api/__init__.py`, `config.py`, `db.py`, `main.py`, `routes/__init__.py`, `routes/health.py`
- Create: `portal/api/alembic.ini`, `portal/api/migrations/env.py`, `portal/api/migrations/script.py.mako`, `portal/api/migrations/versions/0001_extensions.py`
- Create: `portal/api/tests/__init__.py`, `portal/api/tests/conftest.py`, `portal/api/tests/test_health.py`
- Create: `portal/api/pytest.ini`
- Modify: `.gitignore` (append portal entries)

**Interfaces:**
- Produces: `portal_api.config.Settings` (fields below); `portal_api.main.create_app(settings: Settings | None = None, mailer: Mailer | None = None) -> FastAPI` (the `mailer` parameter is accepted from Task 4 on; in this task the signature is `create_app(settings=None)`); `portal_api.db.get_conn` (FastAPI dependency yielding a `sqlalchemy.Connection` inside a transaction); test fixtures `engine`, `settings`, `client`.

- [ ] **Step 1: Dev services**

`portal/deploy/compose.dev.yml`:

```yaml
# Development services only: the API and web app run on the host.
# Postgres on 5433 so it never collides with another local Postgres.
name: portal-dev
services:
  db:
    image: postgis/postgis:17-3.5
    environment:
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: portal
      POSTGRES_DB: portal
    ports: ["127.0.0.1:5433:5432"]
    volumes: [portal-dev-db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U portal"]
      interval: 2s
      retries: 30
  mail:
    image: axllent/mailpit:v1.27
    ports: ["127.0.0.1:1025:1025", "127.0.0.1:8025:8025"]
volumes:
  portal-dev-db:
```

Run: `docker compose -f portal/deploy/compose.dev.yml up -d --wait`
Expected: both services `Healthy`/`Started`. If the `axllent/mailpit:v1.27` tag does not exist,
use the newest `v1.x` tag listed on Docker Hub and record the change in the commit message.

- [ ] **Step 2: Python environment**

`portal/api/requirements.txt`:

```
fastapi==0.143.1
uvicorn[standard]==0.54.0
sqlalchemy==2.1.4
psycopg[binary]==3.3.6
alembic==1.20.0
pydantic-settings==2.16.0
email-validator==2.3.0
```

`portal/api/requirements-dev.txt`:

```
-r requirements.txt
pytest==9.1.1
httpx==0.28.1
```

Run:

```bash
/opt/homebrew/bin/python3.14 -m venv portal/api/.venv
```

```bash
portal/api/.venv/bin/pip install -r portal/api/requirements-dev.txt
```

Expected: installs without error.

Append to `.gitignore`:

```
# Applicant Portal
portal/api/.venv/
portal/web/node_modules/
portal/web/dist/
portal/deploy/.env
```

- [ ] **Step 3: Write the failing test**

`portal/api/pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = -q
```

`portal/api/tests/__init__.py`: empty.

`portal/api/tests/conftest.py`:

```python
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


@pytest.fixture
def settings():
    return Settings(
        database_url=TEST_URL,
        public_base_url="http://testserver",
        cookie_secure=False,
    )


@pytest.fixture
def client(engine, settings):
    with TestClient(create_app(settings)) as c:
        yield c
```

`portal/api/tests/test_health.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd portal/api && .venv/bin/pytest tests/test_health.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'portal_api'`.

- [ ] **Step 5: Write the implementation**

`portal/api/portal_api/__init__.py`: empty.

`portal/api/portal_api/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from PORTAL_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="PORTAL_")

    database_url: str = "postgresql+psycopg://portal:portal@localhost:5433/portal"
    # Where applicants open the web app; sign-in links point here.
    public_base_url: str = "http://localhost:5173"
    # False only in local development over plain http.
    cookie_secure: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "Town of Newcastle Permits <permits@localhost>"
    signin_link_minutes: int = 15
    session_days: int = 14
    # Sign-in link requests allowed per hour.
    signin_limit_per_email: int = 5
    signin_limit_per_ip: int = 20
```

`portal/api/portal_api/db.py`:

```python
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Connection, Engine, create_engine


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def get_conn(request: Request) -> Iterator[Connection]:
    """One transaction per request: committed on success, rolled back on error."""
    with request.app.state.engine.begin() as conn:
        yield conn
```

`portal/api/portal_api/routes/__init__.py`: empty.

`portal/api/portal_api/routes/health.py`:

```python
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()


@router.get("/api/health")
def health(request: Request):
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "degraded", "db": "unavailable"}, status_code=503)
    return {"status": "ok", "db": "ok"}
```

`portal/api/portal_api/main.py`:

```python
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
```

`portal/api/alembic.ini`:

```ini
[alembic]
script_location = migrations
file_template = %%(rev)s_%%(slug)s

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console

[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic

[formatter_generic]
format = %(levelname)s %(message)s
```

`portal/api/migrations/env.py`:

```python
from alembic import context
from sqlalchemy import create_engine

from portal_api.config import Settings

url = context.config.get_main_option("sqlalchemy.url") or Settings().database_url

with create_engine(url).connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
```

`portal/api/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`portal/api/migrations/versions/0001_extensions.py`:

```python
"""PostGIS, for the property lookup in M2.

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis")
```

Make `portal_api` importable from the tests and Alembic: run all API commands from `portal/api`
(pytest adds the rootdir to `sys.path` via `tests/__init__.py`'s package layout; Alembic's
`env.py` imports `portal_api`, so run Alembic as `.venv/bin/python -m alembic` from `portal/api`).

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd portal/api && .venv/bin/pytest`
Expected: `3 passed`.

- [ ] **Step 7: Write `portal/README.md`**

```markdown
# Applicant Portal

The public web app where applicants find out which permit they need and apply for it.
Design: `specs/2026-10-14-applicant-portal-design.md`. Plans: `plans/2026-10-14-applicant-portal-*.md`.

## Development

Start the database and the mail catcher (Mailpit, web view at http://127.0.0.1:8025):

    docker compose -f portal/deploy/compose.dev.yml up -d --wait

API (from `portal/api`):

    /opt/homebrew/bin/python3.14 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/python -m alembic upgrade head
    PORTAL_COOKIE_SECURE=false .venv/bin/uvicorn portal_api.main:create_app --factory --port 8000
    .venv/bin/pytest

Web app (from `portal/web`):

    npm ci && npm run dev      # http://localhost:5173
    npm test
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore portal/README.md portal/deploy/compose.dev.yml portal/api/requirements.txt portal/api/requirements-dev.txt portal/api/pytest.ini portal/api/alembic.ini portal/api/portal_api/__init__.py portal/api/portal_api/config.py portal/api/portal_api/db.py portal/api/portal_api/main.py portal/api/portal_api/routes/__init__.py portal/api/portal_api/routes/health.py portal/api/migrations/env.py portal/api/migrations/script.py.mako portal/api/migrations/versions/0001_extensions.py portal/api/tests/__init__.py portal/api/tests/conftest.py portal/api/tests/test_health.py
git commit -m "portal: API skeleton, dev services, health check (M1 Task 1)"
```

---

## Task 2: Identity tables

**Files:**
- Create: `portal/api/migrations/versions/0002_identity.py`
- Create: `portal/api/tests/test_schema.py`
- Modify: `portal/api/tests/conftest.py` (add the `clean` fixture)

**Interfaces:**
- Produces tables: `applicant(id uuid, email text unique lowercase, name, phone, role in ('applicant','staff','admin'), created_at)`; `signin_token(id, applicant_id, token_hash unique, requested_ip, created_at, expires_at, used_at)`; `session(id, applicant_id, token_hash unique, created_at, expires_at, revoked_at)`; `event(seq, id, at text, actor, kind, payload_json, prev_hash, hash)` with an append-only trigger `event_append_only`.

- [ ] **Step 1: Write the failing test**

`portal/api/tests/test_schema.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, InternalError


def test_email_must_be_lowercase(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email) VALUES ('Ben@Example.com')"))


def test_email_is_unique(engine):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com')"))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com')"))


def test_role_is_restricted(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email, role) VALUES ('b@example.com', 'mayor')"))


def test_event_rows_cannot_be_updated_or_deleted(engine):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO event (id, at, actor, kind, payload_json, prev_hash, hash) "
            "VALUES (gen_random_uuid(), 'now', 'system', 'test', '{}', repeat('0',64), repeat('1',64))"
        ))
    for stmt in ("UPDATE event SET kind='x'", "DELETE FROM event"):
        with pytest.raises(InternalError):
            with engine.begin() as conn:
                conn.execute(text(stmt))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd portal/api && .venv/bin/pytest tests/test_schema.py`
Expected: FAIL — `relation "applicant" does not exist`.

- [ ] **Step 3: Write the migration**

`portal/api/migrations/versions/0002_identity.py`:

```python
"""Applicants, sign-in tokens, sessions, and the append-only event log.

Revision ID: 0002
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE applicant (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email       text NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
        name        text,
        phone       text,
        role        text NOT NULL DEFAULT 'applicant'
                    CHECK (role IN ('applicant', 'staff', 'admin')),
        created_at  timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE signin_token (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id),
        token_hash    text NOT NULL UNIQUE,
        requested_ip  text,
        created_at    timestamptz NOT NULL DEFAULT now(),
        expires_at    timestamptz NOT NULL,
        used_at       timestamptz
    );
    CREATE INDEX signin_token_applicant_created ON signin_token (applicant_id, created_at);
    CREATE INDEX signin_token_ip_created ON signin_token (requested_ip, created_at);

    CREATE TABLE session (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id),
        token_hash    text NOT NULL UNIQUE,
        created_at    timestamptz NOT NULL DEFAULT now(),
        expires_at    timestamptz NOT NULL,
        revoked_at    timestamptz
    );

    -- `at` is the exact ISO string that was hashed, so verification never
    -- depends on how the database round-trips a timestamp.
    CREATE TABLE event (
        seq           bigserial PRIMARY KEY,
        id            uuid NOT NULL UNIQUE,
        at            text NOT NULL,
        actor         text NOT NULL,
        kind          text NOT NULL,
        payload_json  text NOT NULL,
        prev_hash     char(64) NOT NULL,
        hash          char(64) NOT NULL UNIQUE
    );

    CREATE FUNCTION event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'event is append-only';
    END $$;
    CREATE TRIGGER event_append_only BEFORE UPDATE OR DELETE ON event
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE event;
    DROP FUNCTION event_append_only();
    DROP TABLE session;
    DROP TABLE signin_token;
    DROP TABLE applicant;
    """)
```

Add to `portal/api/tests/conftest.py` (after the `engine` fixture). TRUNCATE does not fire row
triggers, so it clears `event` between tests:

```python
@pytest.fixture(autouse=True)
def clean(request):
    yield
    if "engine" in request.fixturenames:
        eng = request.getfixturevalue("engine")
        with eng.begin() as conn:
            conn.execute(text(
                "TRUNCATE applicant, signin_token, session, event RESTART IDENTITY CASCADE"
            ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd portal/api && .venv/bin/pytest`
Expected: `7 passed`.

Also check the downgrade path:

```bash
cd portal/api && PORTAL_DATABASE_URL=postgresql+psycopg://portal:portal@localhost:5433/portal .venv/bin/python -m alembic upgrade head && .venv/bin/python -m alembic downgrade base && .venv/bin/python -m alembic upgrade head
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add portal/api/migrations/versions/0002_identity.py portal/api/tests/test_schema.py portal/api/tests/conftest.py
git commit -m "portal: applicant, sign-in token, session and append-only event tables (M1 Task 2)"
```

---

## Task 3: The hash-chained event log

**Files:**
- Create: `portal/api/portal_api/events.py`
- Create: `portal/api/tests/test_events.py`

**Interfaces:**
- Consumes: the `event` table (Task 2).
- Produces: `append_event(conn: Connection, *, actor: str, kind: str, payload: dict) -> str` (returns the event id); `verify_chain(conn: Connection) -> tuple[bool, int | None]` (`(True, None)` or `(False, seq_of_first_bad_row)`); constant `GENESIS_HASH = "0" * 64`. Actor strings: `"applicant:<uuid>"`, `"system"`.

- [ ] **Step 1: Write the failing test**

`portal/api/tests/test_events.py`:

```python
import threading

from sqlalchemy import text

from portal_api.events import GENESIS_HASH, append_event, verify_chain


def test_first_event_links_to_genesis(engine):
    with engine.begin() as conn:
        append_event(conn, actor="system", kind="test.one", payload={"n": 1})
        row = conn.execute(text("SELECT prev_hash FROM event")).one()
    assert row.prev_hash == GENESIS_HASH


def test_chain_verifies(engine):
    with engine.begin() as conn:
        for n in range(3):
            append_event(conn, actor="system", kind="test.n", payload={"n": n})
    with engine.connect() as conn:
        assert verify_chain(conn) == (True, None)


def test_tampering_is_detected(engine):
    with engine.begin() as conn:
        for n in range(3):
            append_event(conn, actor="system", kind="test.n", payload={"n": n})
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE event DISABLE TRIGGER event_append_only"))
        conn.execute(text("UPDATE event SET payload_json = '{\"n\":99}' WHERE seq = 2"))
        conn.execute(text("ALTER TABLE event ENABLE TRIGGER event_append_only"))
    with engine.connect() as conn:
        assert verify_chain(conn) == (False, 2)


def test_payload_key_order_does_not_change_the_hash(engine):
    with engine.begin() as conn:
        append_event(conn, actor="system", kind="k", payload={"b": 1, "a": 2})
        stored = conn.execute(text("SELECT payload_json FROM event")).scalar()
    assert stored == '{"a":2,"b":1}'


def test_concurrent_appends_keep_one_chain(engine):
    def worker():
        for n in range(20):
            with engine.begin() as conn:
                append_event(conn, actor="system", kind="test.concurrent", payload={"n": n})

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM event")).scalar() == 40
        assert verify_chain(conn) == (True, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd portal/api && .venv/bin/pytest tests/test_events.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'portal_api.events'`.

- [ ] **Step 3: Write the implementation**

`portal/api/portal_api/events.py`:

```python
"""Append-only, hash-chained audit log.

    hash = sha256( prev_hash || id || at || actor || kind || payload_json )

UTF-8, concatenated in that order with no separator; prev_hash of the first row
is GENESIS_HASH. Same formula as the Planning Board Review app
(build/permit-review/app/audit.py). Payloads carry ids, never personal details.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Connection, text

GENESIS_HASH = "0" * 64
# Serialises appends so two transactions can never chain onto the same row.
_APPEND_LOCK = 7_041_955


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prev_hash: str, id_: str, at: str, actor: str, kind: str, payload_json: str) -> str:
    h = hashlib.sha256()
    for part in (prev_hash, id_, at, actor, kind, payload_json):
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def append_event(conn: Connection, *, actor: str, kind: str, payload: dict) -> str:
    conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _APPEND_LOCK})
    prev = conn.execute(text("SELECT hash FROM event ORDER BY seq DESC LIMIT 1")).scalar()
    prev_hash = prev or GENESIS_HASH
    id_ = str(uuid.uuid4())
    at = datetime.now(UTC).isoformat(timespec="microseconds")
    payload_json = _canonical(payload)
    conn.execute(
        text(
            "INSERT INTO event (id, at, actor, kind, payload_json, prev_hash, hash) "
            "VALUES (:id, :at, :actor, :kind, :payload_json, :prev_hash, :hash)"
        ),
        {
            "id": id_, "at": at, "actor": actor, "kind": kind,
            "payload_json": payload_json, "prev_hash": prev_hash,
            "hash": _hash(prev_hash, id_, at, actor, kind, payload_json),
        },
    )
    return id_


def verify_chain(conn: Connection) -> tuple[bool, int | None]:
    expected_prev = GENESIS_HASH
    rows = conn.execute(text(
        "SELECT seq, id, at, actor, kind, payload_json, prev_hash, hash FROM event ORDER BY seq"
    ))
    for r in rows:
        recomputed = _hash(r.prev_hash, str(r.id), r.at, r.actor, r.kind, r.payload_json)
        if r.prev_hash != expected_prev or r.hash != recomputed:
            return False, r.seq
        expected_prev = r.hash
    return True, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd portal/api && .venv/bin/pytest`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```bash
git add portal/api/portal_api/events.py portal/api/tests/test_events.py
git commit -m "portal: hash-chained append-only event log (M1 Task 3)"
```

---

## Task 4: Sending email

**Files:**
- Create: `portal/api/portal_api/mail.py`
- Create: `portal/api/tests/test_mail.py`
- Modify: `portal/api/portal_api/main.py` (accept and store a mailer)
- Modify: `portal/api/tests/conftest.py` (`outbox` fixture; `client` uses it)

**Interfaces:**
- Produces: `Email(to: str, subject: str, body: str)` (frozen dataclass); `Mailer` Protocol with `send(email: Email) -> None`, raising `MailError` on failure; `SmtpMailer(host: str, port: int, sender: str)`; `OutboxMailer` with `.sent: list[Email]` and `.fail: bool`; `signin_email(to: str, link: str, minutes: int) -> Email`; `create_app(settings=None, mailer=None)` stores `app.state.mailer` (default `SmtpMailer` from settings). Fixture `outbox` → the `OutboxMailer` the `client` fixture's app uses.

- [ ] **Step 1: Write the failing test**

`portal/api/tests/test_mail.py`:

```python
import httpx
import pytest

from portal_api.mail import Email, MailError, OutboxMailer, SmtpMailer, signin_email

MAILPIT = "http://127.0.0.1:8025/api/v1/messages"


def test_signin_email_is_plain_and_carries_the_link():
    e = signin_email("a@example.com", "https://x/signin/verify#token=abc", 15)
    assert e.to == "a@example.com"
    assert e.subject == "Your sign-in link for Newcastle permits"
    assert "https://x/signin/verify#token=abc" in e.body
    assert "15 minutes" in e.body
    assert "If you didn't ask for this" in e.body


def test_outbox_records_and_can_fail():
    box = OutboxMailer()
    box.send(Email("a@example.com", "s", "b"))
    assert box.sent == [Email("a@example.com", "s", "b")]
    box.fail = True
    with pytest.raises(MailError):
        box.send(Email("a@example.com", "s", "b"))


def test_header_injection_is_refused():
    with pytest.raises(MailError):
        SmtpMailer("127.0.0.1", 1025, "permits@localhost").send(
            Email("a@example.com\r\nBcc: x@evil.test", "s", "b")
        )


def test_smtp_mailer_delivers_to_mailpit():
    httpx.delete(MAILPIT)
    SmtpMailer("127.0.0.1", 1025, "Newcastle Permits <permits@localhost>").send(
        Email("dev@example.com", "Hello from the portal", "Body text")
    )
    msgs = httpx.get(MAILPIT).json()["messages"]
    assert [m["Subject"] for m in msgs] == ["Hello from the portal"]
    assert msgs[0]["To"][0]["Address"] == "dev@example.com"


def test_unreachable_relay_raises_mail_error():
    with pytest.raises(MailError):
        SmtpMailer("127.0.0.1", 1, "permits@localhost").send(Email("a@example.com", "s", "b"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd portal/api && .venv/bin/pytest tests/test_mail.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'portal_api.mail'`.

- [ ] **Step 3: Write the implementation**

`portal/api/portal_api/mail.py`:

```python
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol


class MailError(Exception):
    """The message could not be handed to the relay."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class Mailer(Protocol):
    def send(self, email: Email) -> None: ...


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str):
        self.host, self.port, self.sender = host, port, sender

    def send(self, email: Email) -> None:
        if any(c in email.to + email.subject for c in "\r\n"):
            raise MailError("line break in a header")
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = email.to
        msg["Subject"] = email.subject
        msg.set_content(email.body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailError(str(exc)) from exc


@dataclass
class OutboxMailer:
    """For tests: keeps messages in memory; set fail=True to simulate a dead relay."""

    sent: list[Email] = field(default_factory=list)
    fail: bool = False

    def send(self, email: Email) -> None:
        if self.fail:
            raise MailError("simulated relay failure")
        self.sent.append(email)


def signin_email(to: str, link: str, minutes: int) -> Email:
    body = (
        "Hello,\n\n"
        "Here is your link to sign in to the Town of Newcastle permit applications site:\n\n"
        f"{link}\n\n"
        f"The link works once and stops working after {minutes} minutes.\n\n"
        "If you didn't ask for this, you can ignore this email. Nobody can sign in without the link.\n\n"
        "Town of Newcastle, Maine\n"
    )
    return Email(to=to, subject="Your sign-in link for Newcastle permits", body=body)
```

Replace `portal/api/portal_api/main.py` with:

```python
from fastapi import FastAPI

from portal_api.config import Settings
from portal_api.db import make_engine
from portal_api.mail import Mailer, SmtpMailer
from portal_api.routes import health


def create_app(settings: Settings | None = None, mailer: Mailer | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Newcastle Applicant Portal", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.mailer = mailer or SmtpMailer(settings.smtp_host, settings.smtp_port, settings.smtp_from)
    app.include_router(health.router)
    return app
```

In `portal/api/tests/conftest.py`, add the import `from portal_api.mail import OutboxMailer`,
add this fixture, and replace the `client` fixture:

```python
@pytest.fixture
def outbox():
    return OutboxMailer()


@pytest.fixture
def client(engine, settings, outbox):
    with TestClient(create_app(settings, outbox)) as c:
        yield c
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd portal/api && .venv/bin/pytest`
Expected: `17 passed`.

- [ ] **Step 5: Commit**

```bash
git add portal/api/portal_api/mail.py portal/api/portal_api/main.py portal/api/tests/test_mail.py portal/api/tests/conftest.py
git commit -m "portal: email sending with an SMTP relay and a test outbox (M1 Task 4)"
```

---

## Task 5: Sign-in links and sessions

**Files:**
- Create: `portal/api/portal_api/auth.py` (token and session logic)
- Create: `portal/api/portal_api/routes/auth.py` (HTTP endpoints)
- Create: `portal/api/tests/test_auth.py`
- Modify: `portal/api/portal_api/main.py` (include the auth router)

**Interfaces:**
- Consumes: `append_event` (Task 3); `Mailer`, `MailError`, `signin_email` (Task 4); `get_conn` (Task 1).
- Produces HTTP API (all JSON):
  - `POST /api/auth/request-link` body `{"email": str}` → `202 {"status": "sent"}`; `422` bad email; `429 {"detail": "too_many_requests"}`; `503 {"detail": "email_unavailable"}`.
  - `POST /api/auth/verify` body `{"token": str}` → `200 {"email": str, "role": str}` and sets cookie `portal_session`; `400 {"detail": "link_invalid"}` for unknown, used or expired.
  - `GET /api/me` → `200 {"email": str, "role": str}` or `401 {"detail": "signed_out"}`.
  - `POST /api/auth/sign-out` → `204`, clears the cookie.
- Produces Python: `portal_api.auth.current_applicant(request, conn) -> Applicant | None` with `Applicant(id: str, email: str, role: str)`; `SESSION_COOKIE = "portal_session"`. Later milestones protect routes with `require_applicant` (a dependency raising 401).
- Event kinds: `signin.requested`, `signin.verified`, `signin.signed_out` — payload `{"applicant_id": ...}` only.

- [ ] **Step 1: Write the failing test**

`portal/api/tests/test_auth.py`:

```python
import re
import threading

from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.auth import redeem_signin_token, token_hash
from portal_api.events import verify_chain
from portal_api.main import create_app


def _token_from(outbox) -> str:
    m = re.search(r"/signin/verify#token=([A-Za-z0-9_\-]+)", outbox.sent[-1].body)
    assert m, outbox.sent[-1].body
    return m.group(1)


def _sign_in(client, outbox, email="a@example.com"):
    assert client.post("/api/auth/request-link", json={"email": email}).status_code == 202
    return client.post("/api/auth/verify", json={"token": _token_from(outbox)})


def test_full_sign_in_flow(client, outbox):
    r = _sign_in(client, outbox)
    assert r.status_code == 200
    assert r.json() == {"email": "a@example.com", "role": "applicant"}
    assert client.get("/api/me").json() == {"email": "a@example.com", "role": "applicant"}


def test_link_points_at_the_web_app_with_token_in_fragment(client, outbox):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    assert "http://testserver/signin/verify#token=" in outbox.sent[-1].body


def test_session_cookie_flags(engine, outbox):
    from portal_api.config import Settings
    from tests.conftest import TEST_URL
    secure = Settings(database_url=TEST_URL, public_base_url="https://testserver", cookie_secure=True)
    with TestClient(create_app(secure, outbox), base_url="https://testserver") as c:
        r = _sign_in(c, outbox)
    cookie = r.headers["set-cookie"]
    assert "portal_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie


def test_email_is_normalised(client, outbox, engine):
    client.post("/api/auth/request-link", json={"email": "  Ben@Example.COM "})
    client.post("/api/auth/request-link", json={"email": "ben@example.com"})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM applicant")).scalar() == 1
    assert {e.to for e in outbox.sent} == {"ben@example.com"}


def test_bad_email_is_422(client):
    assert client.post("/api/auth/request-link", json={"email": "not-an-email"}).status_code == 422


def test_token_is_stored_only_as_a_hash(client, outbox, engine):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    token = _token_from(outbox)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT token_hash FROM signin_token")).scalar()
    assert token not in stored and len(stored) == 64


def test_link_is_single_use(client, outbox):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    token = _token_from(outbox)
    assert client.post("/api/auth/verify", json={"token": token}).status_code == 200
    r = client.post("/api/auth/verify", json={"token": token})
    assert r.status_code == 400 and r.json() == {"detail": "link_invalid"}


def test_expired_link_is_refused(client, outbox, engine):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    with engine.begin() as conn:
        conn.execute(text("UPDATE signin_token SET expires_at = now() - interval '1 second'"))
    r = client.post("/api/auth/verify", json={"token": _token_from(outbox)})
    assert r.status_code == 400 and r.json() == {"detail": "link_invalid"}


def test_link_expires_after_15_minutes(client, outbox, engine):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    with engine.connect() as conn:
        minutes = conn.execute(text(
            "SELECT extract(epoch FROM expires_at - created_at) / 60 FROM signin_token"
        )).scalar()
    assert round(minutes) == 15


def test_unknown_token_is_refused(client):
    r = client.post("/api/auth/verify", json={"token": "nope"})
    assert r.status_code == 400 and r.json() == {"detail": "link_invalid"}


def test_verify_requires_post(client, outbox):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    assert client.get("/api/auth/verify").status_code == 405


def test_concurrent_redeem_succeeds_once(client, outbox, engine):
    # Exercised below the HTTP layer: TestClient is not safe to share across threads.
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    hashed = token_hash(_token_from(outbox))
    results = []

    def go():
        with engine.begin() as conn:
            results.append(redeem_signin_token(conn, hashed))

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(r is not None for r in results) == 1


def test_me_without_session_is_401(client):
    r = client.get("/api/me")
    assert r.status_code == 401 and r.json() == {"detail": "signed_out"}


def test_sign_out_revokes_the_session(client, outbox):
    _sign_in(client, outbox)
    assert client.post("/api/auth/sign-out").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_expired_session_is_signed_out(client, outbox, engine):
    _sign_in(client, outbox)
    with engine.begin() as conn:
        conn.execute(text("UPDATE session SET expires_at = now() - interval '1 second'"))
    assert client.get("/api/me").status_code == 401


def test_rate_limit_per_email(client, outbox):
    for _ in range(5):
        assert client.post("/api/auth/request-link", json={"email": "a@example.com"}).status_code == 202
    r = client.post("/api/auth/request-link", json={"email": "a@example.com"})
    assert r.status_code == 429 and r.json() == {"detail": "too_many_requests"}


def test_rate_limit_per_ip(client, outbox):
    for n in range(20):
        assert client.post("/api/auth/request-link", json={"email": f"p{n}@example.com"}).status_code == 202
    assert client.post("/api/auth/request-link", json={"email": "p99@example.com"}).status_code == 429


def test_mail_failure_returns_503_and_no_token(client, outbox, engine):
    outbox.fail = True
    r = client.post("/api/auth/request-link", json={"email": "a@example.com"})
    assert r.status_code == 503 and r.json() == {"detail": "email_unavailable"}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM signin_token")).scalar() == 0


def test_events_are_logged_without_personal_details(client, outbox, engine):
    _sign_in(client, outbox)
    client.post("/api/auth/sign-out")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT kind, payload_json FROM event ORDER BY seq")).all()
        assert verify_chain(conn) == (True, None)
    assert [r.kind for r in rows] == ["signin.requested", "signin.verified", "signin.signed_out"]
    assert all("@" not in r.payload_json for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd portal/api && .venv/bin/pytest tests/test_auth.py`
Expected: FAIL — `404` on `/api/auth/request-link` (first assertion in most tests).

- [ ] **Step 3: Write the token and session logic**

`portal/api/portal_api/auth.py`:

```python
"""Sign-in links and sessions. Only SHA-256 hashes of tokens are stored."""

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Connection, text

from portal_api.db import get_conn

SESSION_COOKIE = "portal_session"


@dataclass(frozen=True)
class Applicant:
    id: str
    email: str
    role: str


def new_token() -> tuple[str, str]:
    """Returns (token for the applicant, hash for the database)."""
    token = secrets.token_urlsafe(32)
    return token, token_hash(token)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalise_email(email: str) -> str:
    return email.strip().lower()


def upsert_applicant(conn: Connection, email: str) -> str:
    return str(conn.execute(
        text(
            "INSERT INTO applicant (email) VALUES (:email) "
            "ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email RETURNING id"
        ),
        {"email": email},
    ).scalar())


def recent_requests(conn: Connection, *, applicant_id: str, ip: str | None) -> tuple[int, int]:
    by_email = conn.execute(text(
        "SELECT count(*) FROM signin_token WHERE applicant_id = :a "
        "AND created_at > now() - interval '1 hour'"
    ), {"a": applicant_id}).scalar()
    by_ip = conn.execute(text(
        "SELECT count(*) FROM signin_token WHERE requested_ip = :ip "
        "AND created_at > now() - interval '1 hour'"
    ), {"ip": ip}).scalar() if ip else 0
    return by_email, by_ip


def store_signin_token(conn: Connection, *, applicant_id: str, hashed: str, ip: str | None, minutes: int) -> None:
    conn.execute(text(
        "INSERT INTO signin_token (applicant_id, token_hash, requested_ip, expires_at) "
        "VALUES (:a, :h, :ip, now() + make_interval(mins => :m))"
    ), {"a": applicant_id, "h": hashed, "ip": ip, "m": minutes})


def redeem_signin_token(conn: Connection, hashed: str) -> Applicant | None:
    """Marks the token used and returns its applicant, or None if unknown, used or expired.
    The conditional UPDATE is atomic, so two concurrent redemptions cannot both succeed."""
    row = conn.execute(text(
        "UPDATE signin_token SET used_at = now() "
        "WHERE token_hash = :h AND used_at IS NULL AND expires_at > now() "
        "RETURNING applicant_id"
    ), {"h": hashed}).one_or_none()
    if row is None:
        return None
    return _applicant_by_id(conn, str(row.applicant_id))


def create_session(conn: Connection, *, applicant_id: str, days: int) -> str:
    token, hashed = new_token()
    conn.execute(text(
        "INSERT INTO session (applicant_id, token_hash, expires_at) "
        "VALUES (:a, :h, now() + make_interval(days => :d))"
    ), {"a": applicant_id, "h": hashed, "d": days})
    return token


def revoke_session(conn: Connection, token: str) -> str | None:
    row = conn.execute(text(
        "UPDATE session SET revoked_at = now() WHERE token_hash = :h AND revoked_at IS NULL "
        "RETURNING applicant_id"
    ), {"h": token_hash(token)}).one_or_none()
    return str(row.applicant_id) if row else None


def _applicant_by_id(conn: Connection, applicant_id: str) -> Applicant:
    r = conn.execute(text("SELECT id, email, role FROM applicant WHERE id = :a"), {"a": applicant_id}).one()
    return Applicant(id=str(r.id), email=r.email, role=r.role)


def current_applicant(request: Request, conn: Connection) -> Applicant | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = conn.execute(text(
        "SELECT applicant_id FROM session WHERE token_hash = :h "
        "AND revoked_at IS NULL AND expires_at > now()"
    ), {"h": token_hash(token)}).one_or_none()
    return _applicant_by_id(conn, str(row.applicant_id)) if row else None


def require_applicant(request: Request, conn: Connection = Depends(get_conn)) -> Applicant:
    applicant = current_applicant(request, conn)
    if applicant is None:
        raise HTTPException(status_code=401, detail="signed_out")
    return applicant
```

- [ ] **Step 4: Write the endpoints**

`portal/api/portal_api/routes/auth.py`:

```python
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import Connection

from portal_api import auth
from portal_api.db import get_conn
from portal_api.events import append_event
from portal_api.mail import MailError, signin_email

router = APIRouter()


class LinkRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    token: str


@router.post("/api/auth/request-link", status_code=202)
def request_link(body: LinkRequest, request: Request, conn: Connection = Depends(get_conn)):
    settings = request.app.state.settings
    email = auth.normalise_email(body.email)
    ip = request.client.host if request.client else None
    applicant_id = auth.upsert_applicant(conn, email)
    by_email, by_ip = auth.recent_requests(conn, applicant_id=applicant_id, ip=ip)
    if by_email >= settings.signin_limit_per_email or by_ip >= settings.signin_limit_per_ip:
        return JSONResponse({"detail": "too_many_requests"}, status_code=429)
    token, hashed = auth.new_token()
    link = f"{settings.public_base_url}/signin/verify#token={token}"
    # Send first, store second: a link nobody received is never redeemable. If the
    # store fails after a successful send, the emailed link is simply dead.
    try:
        request.app.state.mailer.send(signin_email(email, link, settings.signin_link_minutes))
    except MailError:
        return JSONResponse({"detail": "email_unavailable"}, status_code=503)
    auth.store_signin_token(conn, applicant_id=applicant_id, hashed=hashed, ip=ip,
                            minutes=settings.signin_link_minutes)
    append_event(conn, actor=f"applicant:{applicant_id}", kind="signin.requested",
                 payload={"applicant_id": applicant_id})
    return {"status": "sent"}


@router.post("/api/auth/verify")
def verify(body: VerifyRequest, request: Request, response: Response,
           conn: Connection = Depends(get_conn)):
    settings = request.app.state.settings
    applicant = auth.redeem_signin_token(conn, auth.token_hash(body.token))
    if applicant is None:
        return JSONResponse({"detail": "link_invalid"}, status_code=400)
    session_token = auth.create_session(conn, applicant_id=applicant.id, days=settings.session_days)
    append_event(conn, actor=f"applicant:{applicant.id}", kind="signin.verified",
                 payload={"applicant_id": applicant.id})
    response.set_cookie(
        auth.SESSION_COOKIE, session_token,
        max_age=settings.session_days * 86400, path="/",
        httponly=True, secure=settings.cookie_secure, samesite="lax",
    )
    return {"email": applicant.email, "role": applicant.role}


@router.get("/api/me")
def me(applicant: auth.Applicant = Depends(auth.require_applicant)):
    return {"email": applicant.email, "role": applicant.role}


@router.post("/api/auth/sign-out", status_code=204)
def sign_out(request: Request, conn: Connection = Depends(get_conn)):
    token = request.cookies.get(auth.SESSION_COOKIE)
    applicant_id = auth.revoke_session(conn, token) if token else None
    if applicant_id:
        append_event(conn, actor=f"applicant:{applicant_id}", kind="signin.signed_out",
                     payload={"applicant_id": applicant_id})
    response = Response(status_code=204)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return response
```

In `portal/api/portal_api/main.py`, change the routes import to
`from portal_api.routes import auth as auth_routes, health` and add
`app.include_router(auth_routes.router)` after the health router.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd portal/api && .venv/bin/pytest`
Expected: `36 passed`.

- [ ] **Step 6: Commit**

```bash
git add portal/api/portal_api/auth.py portal/api/portal_api/routes/auth.py portal/api/portal_api/main.py portal/api/tests/test_auth.py
git commit -m "portal: email sign-in links and sessions (M1 Task 5)"
```

---

## Task 6: Web app shell with HeroUI

**Files:**
- Create: `portal/web/package.json`, `portal/web/package-lock.json` (generated), `portal/web/vite.config.ts`, `portal/web/tsconfig.json`, `portal/web/index.html`
- Create: `portal/web/src/main.tsx`, `src/index.css`, `src/App.tsx`, `src/api.ts`, `src/test-setup.ts`
- Create: `portal/web/src/components/Layout.tsx`
- Create: `portal/web/src/pages/Home.tsx`, `SignIn.tsx`, `Verify.tsx`, `MyApplications.tsx`
- Create: `portal/web/src/pages/SignIn.test.tsx`, `Verify.test.tsx`, `MyApplications.test.tsx`

**Interfaces:**
- Consumes: the Task 5 HTTP API.
- Produces: routes `/` (Home), `/signin` (SignIn), `/signin/verify` (Verify), `/my-applications` (MyApplications); `src/api.ts` exports `requestLink(email: string): Promise<"sent" | "too_many_requests" | "email_unavailable" | "invalid_email">`, `verifyToken(token: string): Promise<Me | null>`, `getMe(): Promise<Me | null>`, `signOut(): Promise<void>`, type `Me = { email: string; role: string }`. Later milestones add pages under `src/pages/` and wrap them in `Layout`.

HeroUI v3 notes for the implementer (checked against the 3.2.6 package): no Provider is needed;
styles come from `@import "@heroui/styles";` after `@import "tailwindcss";`; components are
compound (`Card`, `Card.Header`, `Card.Title`, `Card.Content`); `Button` takes `variant`
(`primary`, `secondary`, `tertiary`, `outline`, `ghost`, `danger`) and `onPress`; `TextField`
wraps React Aria's TextField and takes `Label`, `Input`, `Description`, `FieldError` children.
If an import named here does not exist in 3.2.6, check https://heroui.com/llms.txt and use the
documented equivalent — do not switch libraries.

- [ ] **Step 1: Scaffold**

`portal/web/package.json`:

```json
{
  "name": "newcastle-applicant-portal",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@heroui/react": "3.2.6",
    "react": "19.3.1",
    "react-dom": "19.3.1",
    "react-router": "8.4.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "4.3.3",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@testing-library/user-event": "14.6.1",
    "@types/react": "19.2.2",
    "@types/react-dom": "19.2.2",
    "@vitejs/plugin-react": "6.1.2",
    "jsdom": "30.1.2",
    "tailwindcss": "4.3.3",
    "typescript": "5.9.3",
    "vite": "8.3.4",
    "vitest": "5.0.4"
  }
}
```

Before installing, confirm the three versions this plan did not check —
`npm view @testing-library/user-event version`, `npm view @types/react version`,
`npm view @types/react-dom version` — and use the versions printed (exact, no `^`).

Run: `cd portal/web && npm install`
Expected: installs; `package-lock.json` created. If npm reports a peer-dependency conflict, stop
and report it rather than using `--force` or `--legacy-peer-deps`.

`portal/web/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    css: false,
  },
});
```

`portal/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "skipLibCheck": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`portal/web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Permits — Town of Newcastle, Maine</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`portal/web/src/index.css`:

```css
@import "tailwindcss";
@import "@heroui/styles";
```

`portal/web/src/test-setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
```

- [ ] **Step 2: Write the failing tests**

`portal/web/src/pages/SignIn.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import SignIn from "./SignIn";

const renderPage = () => render(<MemoryRouter><SignIn /></MemoryRouter>);

describe("SignIn", () => {
  it("sends a link and tells the person to check their email", async () => {
    const spy = vi.spyOn(api, "requestLink").mockResolvedValue("sent");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(spy).toHaveBeenCalledWith("a@example.com");
    expect(await screen.findByText(/Check your email/)).toBeInTheDocument();
  });

  it("explains a rate limit in plain words", async () => {
    vi.spyOn(api, "requestLink").mockResolvedValue("too_many_requests");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(await screen.findByText(/asked for several links/)).toBeInTheDocument();
  });

  it("explains a mail outage in plain words", async () => {
    vi.spyOn(api, "requestLink").mockResolvedValue("email_unavailable");
    renderPage();
    await userEvent.type(screen.getByLabelText("Your email address"), "a@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(await screen.findByText(/couldn't send the email/)).toBeInTheDocument();
  });
});
```

`portal/web/src/pages/Verify.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import Verify from "./Verify";

const renderAt = (hash: string) => {
  window.location.hash = hash;
  return render(
    <MemoryRouter initialEntries={["/signin/verify"]}>
      <Routes>
        <Route path="/signin/verify" element={<Verify />} />
        <Route path="/my-applications" element={<p>My applications page</p>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("Verify", () => {
  it("redeems the token from the URL fragment with a POST and moves on", async () => {
    const spy = vi.spyOn(api, "verifyToken").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("#token=abc123");
    expect(await screen.findByText("My applications page")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith("abc123");
    expect(window.location.hash).toBe("");
  });

  it("explains a used or expired link and offers a new one", async () => {
    vi.spyOn(api, "verifyToken").mockResolvedValue(null);
    renderAt("#token=old");
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get a new link" })).toHaveAttribute("href", "/signin");
  });

  it("handles a missing token without calling the API", async () => {
    const spy = vi.spyOn(api, "verifyToken");
    renderAt("");
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});
```

`portal/web/src/pages/MyApplications.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import MyApplications from "./MyApplications";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/my-applications"]}>
      <Routes>
        <Route path="/my-applications" element={<MyApplications />} />
        <Route path="/signin" element={<p>Sign in page</p>} />
      </Routes>
    </MemoryRouter>,
  );

describe("MyApplications", () => {
  it("shows who is signed in and an empty list", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderPage();
    expect(await screen.findByText(/a@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/You haven't started any applications yet/)).toBeInTheDocument();
  });

  it("sends a signed-out visitor to sign in", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    renderPage();
    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd portal/web && npm test`
Expected: FAIL — cannot resolve `./SignIn`, `./Verify`, `./MyApplications`, `../api`.

- [ ] **Step 4: Write the implementation**

`portal/web/src/api.ts`:

```ts
export type Me = { email: string; role: string };
export type LinkResult = "sent" | "too_many_requests" | "email_unavailable" | "invalid_email";

const json = { "Content-Type": "application/json" };

export async function requestLink(email: string): Promise<LinkResult> {
  const r = await fetch("/api/auth/request-link", { method: "POST", headers: json, body: JSON.stringify({ email }) });
  if (r.status === 202) return "sent";
  if (r.status === 429) return "too_many_requests";
  if (r.status === 422) return "invalid_email";
  return "email_unavailable";
}

export async function verifyToken(token: string): Promise<Me | null> {
  const r = await fetch("/api/auth/verify", { method: "POST", headers: json, body: JSON.stringify({ token }) });
  return r.ok ? ((await r.json()) as Me) : null;
}

export async function getMe(): Promise<Me | null> {
  const r = await fetch("/api/me");
  return r.ok ? ((await r.json()) as Me) : null;
}

export async function signOut(): Promise<void> {
  await fetch("/api/auth/sign-out", { method: "POST" });
}
```

`portal/web/src/components/Layout.tsx`:

```tsx
import type { ReactNode } from "react";
import { Link } from "react-router";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-separator">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-semibold">Town of Newcastle · Permits</Link>
          <Link to="/my-applications" className="text-sm underline">My applications</Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
    </div>
  );
}
```

`portal/web/src/pages/Home.tsx`:

```tsx
import { Card } from "@heroui/react";
import { Link } from "react-router";

export default function Home() {
  return (
    <Card>
      <Card.Header>
        <Card.Title>Planning a project in Newcastle?</Card.Title>
        <Card.Description>
          Answer a few simple questions to find out which permit you need, then apply online.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <p>This part of the site is being built. You can already sign in to try it.</p>
        <Link to="/signin" className="underline">Sign in</Link>
      </Card.Content>
    </Card>
  );
}
```

`portal/web/src/pages/SignIn.tsx`:

```tsx
import { Button, Card, Description, Form, Input, Label, TextField } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { requestLink, type LinkResult } from "../api";

const MESSAGES: Record<Exclude<LinkResult, "sent">, string> = {
  too_many_requests: "You've asked for several links in the last hour. Please wait a while and try again.",
  email_unavailable: "We couldn't send the email just now. Please try again in a few minutes.",
  invalid_email: "That doesn't look like an email address. Please check it and try again.",
};

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<LinkResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setResult(await requestLink(email));
    setBusy(false);
  }

  if (result === "sent") {
    return (
      <Card>
        <Card.Header>
          <Card.Title>Check your email</Card.Title>
          <Card.Description>
            We sent a sign-in link to {email}. It works once and stops working after 15 minutes.
          </Card.Description>
        </Card.Header>
      </Card>
    );
  }

  return (
    <Card>
      <Card.Header>
        <Card.Title>Sign in</Card.Title>
        <Card.Description>No password needed. We'll email you a link.</Card.Description>
      </Card.Header>
      <Card.Content>
        <Form onSubmit={onSubmit} className="flex flex-col gap-4">
          <TextField type="email" isRequired value={email} onChange={setEmail}>
            <Label>Your email address</Label>
            <Input />
            <Description>We only use it to send you links and updates about your applications.</Description>
          </TextField>
          {result && <p role="alert">{MESSAGES[result]}</p>}
          <Button type="submit" variant="primary" isDisabled={busy}>Email me a sign-in link</Button>
        </Form>
      </Card.Content>
    </Card>
  );
}
```

`portal/web/src/pages/Verify.tsx`:

```tsx
import { Card } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { verifyToken } from "../api";

export default function Verify() {
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    // React StrictMode runs effects twice in development; a token works once.
    if (started.current) return;
    started.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    // Remove the token from the address bar and history straight away.
    history.replaceState(null, "", window.location.pathname + window.location.search);
    if (!token) {
      setFailed(true);
      return;
    }
    verifyToken(token).then((me) => (me ? navigate("/my-applications", { replace: true }) : setFailed(true)));
  }, [navigate]);

  if (!failed) return <p>Signing you in…</p>;
  return (
    <Card>
      <Card.Header>
        <Card.Title>That link didn't work</Card.Title>
        <Card.Description>The link has expired or was already used. Sign-in links work once, for 15 minutes.</Card.Description>
      </Card.Header>
      <Card.Content>
        <Link to="/signin" className="underline">Get a new link</Link>
      </Card.Content>
    </Card>
  );
}
```

`portal/web/src/pages/MyApplications.tsx`:

```tsx
import { Button, Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { getMe, signOut, type Me } from "../api";

export default function MyApplications() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    getMe().then((m) => (m ? setMe(m) : navigate("/signin", { replace: true })));
  }, [navigate]);

  if (!me) return <p>Loading…</p>;
  return (
    <Card>
      <Card.Header>
        <Card.Title>My applications</Card.Title>
        <Card.Description>Signed in as {me.email}</Card.Description>
      </Card.Header>
      <Card.Content>
        <p>You haven't started any applications yet.</p>
      </Card.Content>
      <Card.Footer>
        <Button variant="secondary" onPress={() => signOut().then(() => navigate("/", { replace: true }))}>
          Sign out
        </Button>
      </Card.Footer>
    </Card>
  );
}
```

`portal/web/src/App.tsx`:

```tsx
import { BrowserRouter, Route, Routes } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MyApplications from "./pages/MyApplications";
import SignIn from "./pages/SignIn";
import Verify from "./pages/Verify";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signin/verify" element={<Verify />} />
          <Route path="/my-applications" element={<MyApplications />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
```

`portal/web/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 5: Run tests and the build**

Run: `cd portal/web && npm test`
Expected: `8 passed`.

Run: `cd portal/web && npm run build`
Expected: type-check clean; `dist/` written.

- [ ] **Step 6: Try it by hand**

With the dev services up, start the API (`PORTAL_COOKIE_SECURE=false`, see `portal/README.md`) and
`npm run dev`. At http://localhost:5173: sign in with any address, open the link from Mailpit
(http://127.0.0.1:8025), land on "My applications", sign out. Open the same link again: "That link
didn't work". Check at a 375 px wide window that nothing overflows.

- [ ] **Step 7: Commit**

```bash
git add portal/web/package.json portal/web/package-lock.json portal/web/vite.config.ts portal/web/tsconfig.json portal/web/index.html portal/web/src/main.tsx portal/web/src/index.css portal/web/src/App.tsx portal/web/src/api.ts portal/web/src/test-setup.ts portal/web/src/components/Layout.tsx portal/web/src/pages/Home.tsx portal/web/src/pages/SignIn.tsx portal/web/src/pages/Verify.tsx portal/web/src/pages/MyApplications.tsx portal/web/src/pages/SignIn.test.tsx portal/web/src/pages/Verify.test.tsx portal/web/src/pages/MyApplications.test.tsx
git commit -m "portal: React + HeroUI shell with email sign-in pages (M1 Task 6)"
```

---

## Task 7: CI job

**Files:**
- Create: `.github/workflows/portal.yml`

**Interfaces:**
- Consumes: `portal/api/requirements-dev.txt`, `portal/web/package-lock.json`, the test commands above.

- [ ] **Step 1: Write the workflow**

`.github/workflows/portal.yml`:

```yaml
# Applicant Portal CI. Separate from build-tests.yml on purpose: the portal's
# tests take about a minute and must not wait on the document-build suite.
name: portal

on:
  pull_request:
    paths: ["portal/**", ".github/workflows/portal.yml"]
  push:
    branches: [main]
    paths: ["portal/**", ".github/workflows/portal.yml"]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgis/postgis:17-3.5
        env:
          POSTGRES_USER: portal
          POSTGRES_PASSWORD: portal
          POSTGRES_DB: portal
        ports: ["5433:5432"]
        options: >-
          --health-cmd "pg_isready -U portal" --health-interval 2s --health-retries 30
      mail:
        image: axllent/mailpit:v1.27
        ports: ["1025:1025", "8025:8025"]
    defaults:
      run:
        working-directory: portal/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: python -m pip install -r requirements-dev.txt
      - run: python -m pytest

  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: portal/web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
          cache: npm
          cache-dependency-path: portal/web/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
```

Use the same `mailpit` tag Task 1 settled on.

- [ ] **Step 2: Check the YAML parses**

Run: `/opt/homebrew/bin/python3.14 -c "import yaml" 2>/dev/null || portal/api/.venv/bin/pip install pyyaml==6.0.3` then
`portal/api/.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/portal.yml')); print('ok')"`
Expected: `ok`. (The job itself runs when the chair pushes the branch; it is not pushed by this task.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/portal.yml
git commit -m "portal: CI job for the API and web app (M1 Task 7)"
```

---

## Task 8: Deployment on the VM

Needs Task 0 Step 3. **Building the images and running the stack locally needs no permission;
copying to or running anything on the VM does — ask the chair in chat first.**

**Files:**
- Create: `portal/api/Dockerfile`, `portal/web/Dockerfile`, `portal/web/.dockerignore`
- Create: `portal/deploy/compose.yml`, `portal/deploy/Caddyfile`, `portal/deploy/env.example`
- Create: `portal/deploy/README.md`

**Interfaces:**
- Consumes: everything above. Environment variables in `portal/deploy/.env` (gitignored), shaped by `env.example`.

- [ ] **Step 1: Images**

`portal/api/Dockerfile`:

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY migrations ./migrations
COPY portal_api ./portal_api
USER nobody
# Migrate, then serve. --proxy-headers so rate limits see the visitor's IP, not Caddy's.
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn portal_api.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
```

`portal/web/Dockerfile` (builds static files into a Caddy image):

```dockerfile
FROM node:24-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2
COPY --from=build /web/dist /srv
```

`portal/web/.dockerignore` (keeps the Mac's `node_modules` out of the Linux build):

```
node_modules
dist
```

- [ ] **Step 2: Compose and Caddy**

`portal/deploy/compose.yml`:

```yaml
name: portal
services:
  db:
    image: postgis/postgis:17-3.5
    restart: unless-stopped
    environment:
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set in .env}
      POSTGRES_DB: portal
    volumes: [db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U portal"]
      interval: 5s
      retries: 20
  api:
    build: ../api
    restart: unless-stopped
    depends_on:
      db: { condition: service_healthy }
    environment:
      PORTAL_DATABASE_URL: postgresql+psycopg://portal:${POSTGRES_PASSWORD}@db:5432/portal
      PORTAL_PUBLIC_BASE_URL: https://${PORTAL_HOST:?set in .env}
      PORTAL_SMTP_HOST: ${SMTP_HOST:?set in .env}
      PORTAL_SMTP_PORT: ${SMTP_PORT:-587}
      PORTAL_SMTP_FROM: ${SMTP_FROM:?set in .env}
  web:
    build: ../web
    restart: unless-stopped
    depends_on: [api]
    ports: ["80:80", "443:443"]
    environment:
      PORTAL_HOST: ${PORTAL_HOST}
      PORTAL_TLS: ${PORTAL_TLS:-}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
volumes:
  db:
  caddy-data:
```

`portal/deploy/Caddyfile`:

```
{$PORTAL_HOST} {
	{$PORTAL_TLS}
	encode zstd gzip
	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options nosniff
		Referrer-Policy no-referrer
		X-Frame-Options DENY
	}
	handle /api/* {
		reverse_proxy api:8000
	}
	handle {
		root * /srv
		try_files {path} /index.html
		file_server
	}
}
```

`portal/deploy/env.example`:

```
# Copy to .env (gitignored) on the VM and fill in.
PORTAL_HOST=permits-dev.example.org
# Leave empty for a public host name (Caddy gets a Let's Encrypt certificate).
# Set to "tls internal" for an IP address or a name only your network resolves.
PORTAL_TLS=
POSTGRES_PASSWORD=change-me
SMTP_HOST=smtp.example.org
SMTP_PORT=587
SMTP_FROM=Town of Newcastle Permits <permits@example.org>
```

Note: `SmtpMailer` (Task 4) speaks plain SMTP without login or STARTTLS. If the chosen relay
requires either (most do on port 587), stop and report — adding authenticated, encrypted SMTP is a
small follow-up task with its own test, not something to improvise here.

- [ ] **Step 3: Build and run the full stack locally**

```bash
cp portal/deploy/env.example portal/deploy/.env
```

Edit `portal/deploy/.env`: `PORTAL_HOST=localhost`, `PORTAL_TLS=tls internal`, `SMTP_HOST=host.docker.internal`, `SMTP_PORT=1025` (the dev Mailpit).

```bash
docker compose -f portal/deploy/compose.yml --env-file portal/deploy/.env up -d --build --wait
```

```bash
curl -sk https://localhost/api/health
```

Expected: `{"status":"ok","db":"ok"}`. Then sign in through https://localhost in a browser (accept
the local certificate) and confirm the link arrives in Mailpit.

- [ ] **Step 4: Write `portal/deploy/README.md`**

```markdown
# Deploying the Applicant Portal

The VM needs Docker Engine with the Compose plugin and ports 80 and 443 open.

1. Copy the repository's `portal/` folder to the VM (or clone the repo there).
2. `cp portal/deploy/env.example portal/deploy/.env` and fill it in. Never commit `.env`.
3. `docker compose -f portal/deploy/compose.yml --env-file portal/deploy/.env up -d --build --wait`
4. Check: `curl -s https://$PORTAL_HOST/api/health` prints `{"status":"ok","db":"ok"}`.

Updating: pull the new code, then repeat step 3. Migrations run when the API container starts.

Moving to a managed platform later: point `PORTAL_DATABASE_URL` at managed Postgres with PostGIS,
run the `api` and `web` images on any container host, and set the SMTP variables for the relay.
Nothing in the code is tied to this VM.

Backups are set up in Milestone 7. Until then the database lives only in the `db` volume on the VM.
```

- [ ] **Step 5: Deploy to the VM — only after the chair says go in chat**

Ask the chair for the go-ahead, naming the VM and host name. Then follow `portal/deploy/README.md`
on the VM. Done when `curl -s https://<PORTAL_HOST>/api/health` prints `{"status":"ok","db":"ok"}`
from the Mac, and a sign-in link sent to the chair's address arrives and signs in.

- [ ] **Step 6: Commit**

```bash
git add portal/api/Dockerfile portal/web/Dockerfile portal/web/.dockerignore portal/deploy/compose.yml portal/deploy/Caddyfile portal/deploy/env.example portal/deploy/README.md
git commit -m "portal: Compose + Caddy deployment for the VM (M1 Task 8)"
```

---

## Milestone 1 done when

- `cd portal/api && .venv/bin/pytest` → `36 passed`; `cd portal/web && npm test` → `8 passed`;
  `npm run build` clean.
- The full stack runs locally under `compose.yml` over HTTPS with a working sign-in.
- On the VM (after the chair's go-ahead): `/api/health` OK over HTTPS and a real sign-in works.
- One fresh-context review of the whole M1 branch (the chair's standing rule), findings ruled on.
- Then write `plans/<date>-applicant-portal-m2-property.md` against the code as it now exists.
