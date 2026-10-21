"""Where uploaded files live: any S3-compatible object store (S3, R2, or RustFS on the
VM), reached only by the API. The browser never talks to the store; files are
streamed back through the API to the people allowed to see them."""

from collections.abc import Iterator
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


class StoreUnavailable(Exception):
    pass


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> Iterator[bytes]: ...


class S3Store:
    def __init__(self, settings):
        self.settings = settings
        self.bucket = settings.s3_bucket
        self._ready = False
        self._client = None

    @property
    def client(self):
        # Built on first use: making a boto3 client is slow, and most app instances never upload.
        if self._client is None:
            s = self.settings
            self._client = boto3.client(
                "s3", endpoint_url=s.s3_endpoint or None, region_name=s.s3_region,
                aws_access_key_id=s.s3_access_key or None, aws_secret_access_key=s.s3_secret_key or None,
                config=Config(s3={"addressing_style": "path"}, connect_timeout=5, read_timeout=30,
                              retries={"max_attempts": 2}),
            )
        return self._client

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket", "NotFound"):
                raise
            self.client.create_bucket(Bucket=self.bucket)
        self._ready = True

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            if not self._ready:
                self.ensure_bucket()
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        except (BotoCoreError, ClientError) as e:
            raise StoreUnavailable(str(e)) from e

    def get(self, key: str) -> Iterator[bytes]:
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        except (BotoCoreError, ClientError) as e:
            raise StoreUnavailable(str(e)) from e
        return body.iter_chunks(chunk_size=256 * 1024)


class MemoryStore:
    """For tests and local experiments."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def get(self, key: str) -> Iterator[bytes]:
        data, _ = self.objects[key]
        return iter([data])
