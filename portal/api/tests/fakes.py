"""Test doubles for the file store's and scanner's neighbours. Never imported by portal_api."""

from portal_api.scan import ScanResult, ScannerUnavailable

# The standard antivirus test string (EICAR); harmless, and every scanner flags it.
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class FakeScanner:
    def __init__(self, down: bool = False):
        self.down = down
        self.scanned = 0

    def scan(self, data: bytes) -> ScanResult:
        if self.down:
            raise ScannerUnavailable("scanner is down")
        self.scanned += 1
        return ScanResult(False, "Eicar-Test-Signature") if EICAR in data else ScanResult(True, None)
