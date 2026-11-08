"""Article 9's defined terms, for the entries that use them (design 2, §6).

The portal's vendored ruleset doesn't carry the definitions file and must not be edited, so the
terms are read from the permit-review copy of the same ruleset and checked against the pinned
manifest's hash. Where that copy isn't there (the API's container has no `build/`), the check is
skipped, and the library says so.
"""

import hashlib
import json
from pathlib import Path

from portal_api.ruleset import PINNED_KEY

from .model import LibraryError

_REPO = Path(__file__).resolve().parents[4]
TERMS_FILE = _REPO / "build" / "permit-review" / "rulesets" / PINNED_KEY / "definitions.json"
_MANIFEST = Path(__file__).resolve().parents[1] / "rulesets" / PINNED_KEY / "manifest.json"


def article_9_terms(path: Path = TERMS_FILE) -> frozenset[str] | None:
    """The defined terms, lower-cased, or None when the file isn't on this machine."""
    if not path.exists():
        return None
    body = path.read_bytes()
    pinned = json.loads(_MANIFEST.read_text())["content_sha256"]["definitions"]
    if hashlib.sha256(body).hexdigest() != pinned:
        raise LibraryError(f"{path}: does not match the pinned ruleset's definitions")
    return frozenset(t["term"].lower() for t in json.loads(body)["definitions"])
