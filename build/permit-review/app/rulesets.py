"""Implements CONTRACT.md §4 (ruleset JSON schemas, load path) and §1 S8 (the
binding gate).

Loads the BUILD OUTPUT under `rulesets/<ruleset_key>/` -- `manifest.json`,
`districts.json`, `use-matrix.json` -- read-only, at runtime. Per CONTRACT.md
§4's preamble: "Runtime never re-parses repo source." Nothing in this module
ever reads `source/article-02*.{json,typ}`; that is `ruleset_build/`'s job,
offline, before this module ever runs.

Caching: each ruleset_key's parsed+indexed Ruleset is built once per process
and reused (the files are build output, not runtime state -- they only change
by re-running `ruleset_build/`, which happens between process restarts).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import RULESETS_DIR


class RulesetNotFound(LookupError):
    """No rulesets/<key>/ directory, or it is missing one of the three
    required files (manifest.json, districts.json, use-matrix.json)."""


class NonBindingRuleset(PermissionError):
    """CONTRACT.md §1 S8 -- a non-binding ruleset (manifest.binding is false)
    was requested through require_binding(). A real (non-scratch) case MUST
    NOT be reviewed against, or cite, this ruleset."""


@dataclass(frozen=True)
class Ruleset:
    """The loaded, read-only shape of one `rulesets/<ruleset_key>/`
    directory. Attribute names (`manifest`, `districts`, `use_matrix`) match
    CONTRACT.md §4's three file schemas one-to-one -- each attribute is that
    file's full parsed JSON object, not a subset.
    """

    ruleset_key: str
    manifest: dict[str, Any]
    districts: dict[str, Any]  # full districts.json (has a top-level "districts" list)
    use_matrix: dict[str, Any]  # full use-matrix.json

    # Convenience indices, built once at load time so callers never scan a
    # list at request time. Not part of CONTRACT.md's file schema -- purely
    # runtime sugar over the three fields above.
    districts_by_key: dict[str, dict[str, Any]] = field(repr=False, compare=False)
    uses_by_key: dict[str, dict[str, Any]] = field(repr=False, compare=False)
    cells_by_pair: dict[tuple[str, str], dict[str, Any]] = field(repr=False, compare=False)

    @property
    def binding(self) -> bool:
        return bool(self.manifest.get("binding"))


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_ruleset(ruleset_key: str) -> Ruleset:
    base = RULESETS_DIR / ruleset_key
    manifest_path = base / "manifest.json"
    districts_path = base / "districts.json"
    use_matrix_path = base / "use-matrix.json"

    missing = [p.name for p in (manifest_path, districts_path, use_matrix_path) if not p.exists()]
    if missing:
        raise RulesetNotFound(
            f"ruleset {ruleset_key!r} is incomplete under {base} -- missing {missing}. "
            f"Build it with ruleset_build/lift_districts.py, lift_use_matrix.py and "
            f"lift_manifest.py (districts.json is blocked until DECISIONS-NEEDED.md's "
            f"open blocking items are resolved -- see overrides/dimension-qualifiers.json)."
        )

    manifest = _read_json(manifest_path)
    districts = _read_json(districts_path)
    use_matrix = _read_json(use_matrix_path)

    districts_by_key = {d["district_key"]: d for d in districts["districts"]}
    uses_by_key = {u["use_key"]: u for u in use_matrix["uses"]}
    cells_by_pair = {(c["district_key"], c["use_key"]): c for c in use_matrix["cells"]}

    return Ruleset(
        ruleset_key=ruleset_key,
        manifest=manifest,
        districts=districts,
        use_matrix=use_matrix,
        districts_by_key=districts_by_key,
        uses_by_key=uses_by_key,
        cells_by_pair=cells_by_pair,
    )


_CACHE: dict[str, Ruleset] = {}


def load_ruleset(key: str) -> Ruleset:
    """Load (and cache) rulesets/<key>/. Raises RulesetNotFound if the
    directory or any of its three required files is missing. Does NOT check
    the binding gate -- a scratch/dry-run case may legitimately load a
    non-binding (draft) ruleset; require_binding() below is the enforcement
    point for real cases (CONTRACT.md §1 S8)."""
    if key not in _CACHE:
        _CACHE[key] = _build_ruleset(key)
    return _CACHE[key]


def require_binding(key: str) -> Ruleset:
    """Load `key` and enforce CONTRACT.md §1 S8: raise NonBindingRuleset if
    it is not binding. Call this (never load_ruleset() alone) anywhere a REAL
    case is about to cite or be reviewed against a ruleset."""
    rs = load_ruleset(key)
    if not rs.binding:
        raise NonBindingRuleset(
            f"ruleset {key!r} is not binding (manifest.binding=false); a real case "
            f"must cite the adopted Code. Pass scratch=true to dry-run a draft ruleset."
        )
    return rs


def clear_cache() -> None:
    """Test-only: drop cached rulesets so a subsequent load_ruleset() call
    re-reads disk. Production code never needs this -- build output does not
    change within a running process."""
    _CACHE.clear()
