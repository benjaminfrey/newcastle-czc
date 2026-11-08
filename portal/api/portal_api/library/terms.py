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

def terms_file(here: Path) -> Path | None:
    """The permit-review copy of the definitions, in the repo above this package, or None where the
    package isn't in the repo (the API's container installs it at /app/portal_api)."""
    parents = here.parents
    if len(parents) < 5:
        return None
    return parents[4] / "build" / "permit-review" / "rulesets" / PINNED_KEY / "definitions.json"


TERMS_FILE = terms_file(Path(__file__).resolve())
_MANIFEST = Path(__file__).resolve().parents[1] / "rulesets" / PINNED_KEY / "manifest.json"


def article_9_terms(path: Path | None = TERMS_FILE) -> frozenset[str] | None:
    """The defined terms, lower-cased, or None when the file isn't on this machine."""
    if path is None or not path.exists():
        return None
    body = path.read_bytes()
    pinned = json.loads(_MANIFEST.read_text())["content_sha256"]["definitions"]
    if hashlib.sha256(body).hexdigest() != pinned:
        raise LibraryError(f"{path}: does not match the pinned ruleset's definitions")
    return frozenset(t["term"].lower() for t in json.loads(body)["definitions"])
