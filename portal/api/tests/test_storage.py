import os
import uuid

import pytest

from portal_api.config import Settings
from portal_api.storage import MemoryStore, S3Store, StoreUnavailable


def test_memory_store_round_trip():
    s = MemoryStore()
    s.put("a/b", b"hello", "application/pdf")
    assert b"".join(s.get("a/b")) == b"hello"
    with pytest.raises(KeyError):
        s.get("missing")


@pytest.mark.skipif(not os.environ.get("PORTAL_TEST_S3_ENDPOINT"), reason="needs an S3-compatible server")
def test_s3_store_round_trip():
    s = S3Store(Settings(s3_endpoint=os.environ["PORTAL_TEST_S3_ENDPOINT"],
                         s3_bucket=f"portal-test-{uuid.uuid4().hex[:8]}",
                         s3_access_key=os.environ.get("PORTAL_TEST_S3_ACCESS_KEY", "portal"),
                         s3_secret_key=os.environ.get("PORTAL_TEST_S3_SECRET_KEY", "portal-dev-secret")))
    data = os.urandom(3 * 1024 * 1024)
    s.put("applications/x/y", data, "image/png")
    assert b"".join(s.get("applications/x/y")) == data


def test_unreachable_s3_is_unavailable():
    s = S3Store(Settings(s3_endpoint="http://127.0.0.1:1", s3_access_key="k", s3_secret_key="s"))
    with pytest.raises(StoreUnavailable):
        s.put("k", b"x", "application/pdf")
