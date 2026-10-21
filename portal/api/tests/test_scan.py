import os
import socket
import struct
import threading

import pytest

from portal_api.config import Settings
from portal_api.main import create_app
from portal_api.scan import ClamdScanner, ScannerUnavailable
from tests.fakes import EICAR


def fake_clamd(reply_for):
    """A one-connection clamd that checks zINSTREAM framing and answers reply_for(data)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    seen = {}

    def serve():
        conn, _ = srv.accept()
        with conn:
            f = conn.makefile("rb")
            assert f.read(10) == b"zINSTREAM\0"
            data = b""
            while True:
                (n,) = struct.unpack(">I", f.read(4))
                if n == 0:
                    break
                data += f.read(n)
            seen["data"] = data
            conn.sendall(reply_for(data))
        srv.close()

    threading.Thread(target=serve, daemon=True).start()
    return srv.getsockname()[1], seen


def test_clamd_protocol_clean_and_found():
    port, seen = fake_clamd(lambda d: b"stream: OK\0")
    data = os.urandom(200_000)
    r = ClamdScanner("127.0.0.1", port, chunk=65_536).scan(data)
    assert r.clean and r.signature is None and seen["data"] == data
    port, _ = fake_clamd(lambda d: b"stream: Eicar-Signature FOUND\0")
    r = ClamdScanner("127.0.0.1", port).scan(EICAR)
    assert not r.clean and r.signature == "Eicar-Signature"


def test_clamd_garbage_reply_is_unavailable():
    port, _ = fake_clamd(lambda d: b"INSTREAM size limit exceeded. ERROR\0")
    with pytest.raises(ScannerUnavailable):
        ClamdScanner("127.0.0.1", port).scan(b"x")


def test_clamd_refused_connection_is_unavailable():
    with pytest.raises(ScannerUnavailable):
        ClamdScanner("127.0.0.1", 1, timeout=2).scan(b"x")


@pytest.mark.skipif(not os.environ.get("PORTAL_TEST_CLAMD_HOST"), reason="needs a real clamd")
def test_real_clamd_finds_eicar():
    s = ClamdScanner(os.environ["PORTAL_TEST_CLAMD_HOST"], int(os.environ.get("PORTAL_TEST_CLAMD_PORT", "3310")))
    # EICAR is recognised as a whole file, which is how the upload journey sends it.
    assert not s.scan(EICAR).clean
    assert s.scan(b"%PDF-1.4\nhello\n").clean


def test_production_app_builds_real_scanner_and_store(settings, outbox):
    app = create_app(settings, outbox)
    assert isinstance(app.state.scanner, ClamdScanner)
    assert type(app.state.store).__name__ == "S3Store"
    app.state.engine.dispose()


def test_settings_defaults():
    s = Settings()
    assert s.upload_max_bytes == 26_214_400 and s.upload_limit_per_hour == 60
    assert s.s3_bucket == "portal-uploads" and s.clamd_port == 3310
