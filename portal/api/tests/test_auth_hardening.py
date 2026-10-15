"""Fixes from the fresh security review after M1 Task 5 (findings 1-5)."""

import asyncio
import json
import threading

from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.mail import OutboxMailer
from portal_api.main import create_app
from tests.test_auth import _token_from


def _client_from(settings, outbox, ip):
    return TestClient(create_app(settings, outbox), client=(ip, 50000))


def _request(c, email):
    return c.post("/api/auth/request-link", json={"email": email}).status_code


# Finding 1: the transaction must be committed before the response leaves.

def test_session_is_committed_before_the_response_starts(engine, settings, outbox, client):
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    token = _token_from(outbox)
    app = create_app(settings, outbox)
    seen = {}

    async def run():
        body = json.dumps({"token": token}).encode()
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/api/auth/verify", "raw_path": b"/api/auth/verify",
            "query_string": b"", "root_path": "", "client": ("1.2.3.4", 1), "server": ("testserver", 80),
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())],
        }
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(3600)

        async def send(message):
            if message["type"] == "http.response.start" and "status" not in seen:
                seen["status"] = message["status"]
                with engine.connect() as conn:
                    seen["sessions"] = conn.execute(text("SELECT count(*) FROM session")).scalar()

        await app(scope, receive, send)

    asyncio.run(run())
    assert seen == {"status": 200, "sessions": 1}


# Finding 2: a stranger must not be able to lock a resident out.

def test_victim_can_still_get_a_link_from_another_address(engine, settings, outbox):
    with _client_from(settings, outbox, "203.0.113.9") as attacker:
        for _ in range(5):
            assert _request(attacker, "victim@example.com") == 202
        assert _request(attacker, "victim@example.com") == 429
    with _client_from(settings, outbox, "198.51.100.7") as victim:
        assert _request(victim, "victim@example.com") == 202


def test_per_email_ceiling_across_addresses(engine, settings, outbox):
    for n in range(20):
        with _client_from(settings, outbox, f"198.51.100.{n + 1}") as c:
            assert _request(c, "busy@example.com") == 202
    with _client_from(settings, outbox, "198.51.100.200") as c:
        assert _request(c, "busy@example.com") == 429


# Finding 3: the per-IP limit holds under IPv6 rotation and under concurrency.

def test_ipv6_addresses_in_one_64_share_a_limit(engine, settings, outbox):
    for n in range(20):
        with _client_from(settings, outbox, f"2001:db8:0:1::{n + 1:x}") as c:
            assert _request(c, f"v6-{n}@example.com") == 202
    with _client_from(settings, outbox, "2001:db8:0:1:ffff::1") as c:
        assert _request(c, "v6-last@example.com") == 429


def test_global_hourly_cap(engine, settings, outbox):
    settings.signin_limit_global = 3
    for n in range(3):
        with _client_from(settings, outbox, f"192.0.2.{n + 1}") as c:
            assert _request(c, f"g{n}@example.com") == 202
    with _client_from(settings, outbox, "192.0.2.99") as c:
        assert _request(c, "g-last@example.com") == 429


def test_parallel_requests_cannot_overshoot_the_ip_limit(engine, settings):
    codes = []

    def go(n):
        with _client_from(settings, OutboxMailer(), "203.0.113.50") as c:
            codes.append(_request(c, f"par{n}@example.com"))

    threads = [threading.Thread(target=go, args=(n,)) for n in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert codes.count(202) == 20 and codes.count(429) == 10


# Finding 4: no database transaction is held open while the email is sent.

class _ProbingMailer(OutboxMailer):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.idle_in_transaction = None

    def send(self, email):
        with self.engine.connect() as conn:
            self.idle_in_transaction = conn.execute(text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND state = 'idle in transaction'"
            )).scalar()
        super().send(email)


def test_no_transaction_is_open_during_the_send(engine, settings):
    mailer = _ProbingMailer(engine)
    with TestClient(create_app(settings, mailer)) as c:
        assert _request(c, "a@example.com") == 202
    assert mailer.idle_in_transaction == 0


# Finding 5: asking for a link does not create an applicant record.

def test_no_applicant_record_until_the_link_is_used(client, outbox, engine):
    client.post("/api/auth/request-link", json={"email": "typo@example.con"})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM applicant")).scalar() == 0
    client.post("/api/auth/verify", json={"token": _token_from(outbox)})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT email FROM applicant")).scalar() == "typo@example.con"


def test_refused_requests_create_no_applicant(client, outbox, engine):
    outbox.fail = True
    client.post("/api/auth/request-link", json={"email": "a@example.com"})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM applicant")).scalar() == 0
