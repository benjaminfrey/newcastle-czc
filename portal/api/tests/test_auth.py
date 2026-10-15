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
