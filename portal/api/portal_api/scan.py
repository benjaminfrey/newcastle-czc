"""Virus scanning with ClamAV's clamd, spoken to directly over TCP (zINSTREAM).

Every upload is scanned before anything is stored. A scanner that cannot be reached,
or answers anything but OK or FOUND, raises ScannerUnavailable and the upload is
refused: nothing is ever accepted unscanned.
"""

import socket
import struct
from dataclasses import dataclass
from typing import Protocol


class ScannerUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    signature: str | None


class Scanner(Protocol):
    def scan(self, data: bytes) -> ScanResult: ...


class ClamdScanner:
    def __init__(self, host: str, port: int, timeout: float = 30, chunk: int = 1024 * 1024):
        self.host, self.port, self.timeout, self.chunk = host, port, timeout, chunk

    def scan(self, data: bytes) -> ScanResult:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
                s.sendall(b"zINSTREAM\0")
                for i in range(0, len(data), self.chunk):
                    part = data[i:i + self.chunk]
                    s.sendall(struct.pack(">I", len(part)) + part)
                s.sendall(struct.pack(">I", 0))
                reply = b""
                while not reply.endswith(b"\0"):
                    got = s.recv(4096)
                    if not got:
                        break
                    reply += got
        except OSError as e:
            raise ScannerUnavailable(str(e)) from e
        answer = reply.rstrip(b"\0").decode("utf-8", "replace").strip()
        if answer == "stream: OK":
            return ScanResult(True, None)
        if answer.startswith("stream: ") and answer.endswith(" FOUND"):
            return ScanResult(False, answer[len("stream: "):-len(" FOUND")])
        raise ScannerUnavailable(f"unexpected clamd reply: {answer[:200]!r}")
