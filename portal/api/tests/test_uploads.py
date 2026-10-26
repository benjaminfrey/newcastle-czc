import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.main import create_app
from portal_api.routes.attachments import bounded_body
from portal_api.storage import MemoryStore, StoreUnavailable
from portal_api.uploads import safe_filename, sniff
from tests.fakes import EICAR, FakeScanner
from tests.test_applications import create, get, lookup_property
from tests.test_auth import _sign_in
from tests.test_property import layers  # noqa: F401  (fixture)

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64
HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64
EXE = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64


class DownStore(MemoryStore):
    def put(self, key, data, content_type):
        raise StoreUnavailable("down")


@pytest.fixture
def parts():
    return {"store": MemoryStore(), "scanner": FakeScanner()}


@pytest.fixture
def make_client(engine, settings, outbox, layers):  # noqa: F811
    settings.allow_stale_parcels = True
    settings.allow_draft_rules = True
    clients = []

    def make(email="alice@example.com", **kw):
        c = TestClient(create_app(settings, outbox, **kw))
        c.__enter__()
        clients.append(c)
        _sign_in(c, outbox, email)
        return c

    yield make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def alice(make_client, parts):
    return make_client(**parts)


def upload(client, app_id, data, name="plan.pdf", ctype="application/pdf", field_id="use_documents", item_id=None):
    form = {"field_id": field_id}
    if item_id:
        form["item_id"] = item_id
    return client.post(f"/api/applications/{app_id}/attachments", data=form, files={"file": (name, data, ctype)})


def stored_rows(engine):
    with engine.begin() as conn:
        return conn.execute(text("SELECT count(*) FROM attachment")).scalar()


def test_sniff():
    assert sniff(PDF) == "application/pdf"
    assert sniff(JPEG) == "image/jpeg"
    assert sniff(PNG) == "image/png"
    assert sniff(HEIC) == "image/heic"
    assert sniff(EXE) is None and sniff(b"") is None and sniff(b"hello") is None


def test_pdf_jpeg_png_heic_accepted(alice, parts):
    app_id = create(alice)
    for data, name in [(PDF, "a.pdf"), (JPEG, "b.jpg"), (PNG, "c.png"), (HEIC, "IMG_0001.HEIC")]:
        r = upload(alice, app_id, data, name=name, ctype="application/octet-stream")
        assert r.status_code == 201, r.text
        assert r.json()["content_type"] == sniff(data) and r.json()["size_bytes"] == len(data)
    listed = get(alice, app_id)["attachments"]
    assert [a["filename"] for a in listed] == ["a.pdf", "b.jpg", "c.png", "IMG_0001.HEIC"]
    assert len(parts["store"].objects) == 4


def test_renamed_executable_is_refused(alice, parts, engine):
    app_id = create(alice)
    r = upload(alice, app_id, EXE, name="plan.pdf", ctype="application/pdf")
    assert r.status_code == 415 and r.json()["detail"] == "unsupported_type"
    assert stored_rows(engine) == 0 and not parts["store"].objects


def test_oversized_upload_is_refused(alice, settings, parts, engine):
    settings.upload_max_bytes = 1000
    app_id = create(alice)
    r = upload(alice, app_id, PDF + b"x" * 2000)
    assert r.status_code == 413 and r.json()["detail"] == "too_large"
    assert stored_rows(engine) == 0 and parts["scanner"].scanned == 0


def test_oversized_upload_is_refused_without_reading_it_all():
    sent = {"bytes": 0}

    class Req:
        headers = {}

        async def stream(self):
            for _ in range(40):
                sent["bytes"] += 1_000_000
                yield b"x" * 1_000_000

    assert asyncio.run(bounded_body(Req(), 5_000_000)) is None
    assert sent["bytes"] <= 6_000_000

    class Declared(Req):
        headers = {"content-length": str(40_000_000)}

    sent["bytes"] = 0
    assert asyncio.run(bounded_body(Declared(), 5_000_000)) is None
    assert sent["bytes"] == 0


def test_infected_upload_stores_nothing(alice, parts, engine):
    app_id = create(alice)
    r = upload(alice, app_id, EICAR, name="eicar.pdf")
    assert r.status_code == 422 and r.json()["detail"] == "infected"
    assert stored_rows(engine) == 0 and not parts["store"].objects


def test_scanner_down_refuses_upload(make_client, engine):
    store = MemoryStore()
    c = make_client(store=store, scanner=FakeScanner(down=True))
    app_id = create(c)
    r = upload(c, app_id, PDF)
    assert r.status_code == 503 and r.json()["detail"] == "scanner_unavailable"
    assert stored_rows(engine) == 0 and not store.objects


def test_store_down_leaves_no_row(make_client, engine):
    c = make_client(store=DownStore(), scanner=FakeScanner())
    app_id = create(c)
    r = upload(c, app_id, PDF)
    assert r.status_code == 503 and r.json()["detail"] == "store_unavailable"
    assert stored_rows(engine) == 0


def test_upload_limit_per_hour(alice, settings):
    settings.upload_limit_per_hour = 2
    app_id = create(alice)
    assert upload(alice, app_id, PDF).status_code == 201
    assert upload(alice, app_id, EXE).status_code == 415  # refused attempts count too
    assert upload(alice, app_id, PDF).status_code == 429


def test_not_an_upload_field(alice):
    app_id = create(alice)
    assert upload(alice, app_id, PDF, field_id="owner_name").json()["detail"] == "not_an_upload_field"
    assert upload(alice, app_id, PDF, field_id="nope").status_code == 422


def test_upload_field_in_a_hidden_section_needs_its_item(make_client, parts):
    c = make_client(**parts)
    app_id = create(c, form_key="entrance_permit")
    assert upload(c, app_id, PDF, field_id="entrance_sketch").status_code == 201
    assert upload(c, app_id, PDF, field_id="entrance_sketch", item_id="x").json()["detail"] == "wrong_item"


def test_download_is_owner_only_and_not_sniffable(alice, make_client, parts):
    app_id = create(alice)
    att = upload(alice, app_id, PNG, name="site.png").json()
    r = alice.get(f"/api/attachments/{att['id']}")
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-disposition"] == "attachment; filename*=UTF-8''site.png"
    bob = make_client("bob@example.com", **parts)
    assert bob.get(f"/api/attachments/{att['id']}").status_code == 404
    assert bob.request("DELETE", f"/api/attachments/{att['id']}").status_code == 404
    assert bob.post(f"/api/applications/{app_id}/attachments", data={"field_id": "use_documents"},
                    files={"file": ("a.pdf", PDF, "application/pdf")}).status_code == 404
    assert alice.get("/api/attachments/not-a-uuid").status_code == 404


def test_filename_is_sanitised(alice):
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\Users\\ben\\plan.pdf") == "plan.pdf"
    assert safe_filename("a\x00b\x1fc.pdf") == "abc.pdf"
    assert safe_filename("") == "file" and safe_filename("x" * 300 + ".pdf").endswith(".pdf")
    assert len(safe_filename("x" * 300 + ".pdf")) == 200
    app_id = create(alice)
    r = upload(alice, app_id, PDF, name="..\\..\\secret plan.pdf")
    assert r.json()["filename"] == "secret plan.pdf"


def test_removed_attachment_not_listed_but_kept(alice, parts, engine):
    app_id = create(alice)
    att = upload(alice, app_id, PDF).json()
    assert alice.request("DELETE", f"/api/attachments/{att['id']}").status_code == 204
    assert get(alice, app_id)["attachments"] == []
    assert alice.get(f"/api/attachments/{att['id']}").status_code == 404
    assert stored_rows(engine) == 1 and len(parts["store"].objects) == 1
    with engine.begin() as conn:
        kinds = [r.kind for r in conn.execute(text("SELECT kind FROM event WHERE kind LIKE 'attachment.%' ORDER BY seq"))]
        payload = conn.execute(text("SELECT payload_json FROM event WHERE kind = 'attachment.added'")).scalar()
    assert kinds == ["attachment.added", "attachment.removed"]
    assert "plan.pdf" not in payload and "sha256" in payload
