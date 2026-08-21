"""Implements CONTRACT.md §4.5 (rulesets/<key>/manifest.json).

The manifest is pure metadata over the two files ruleset_build's other two
builders (build_districts.py, build_use_matrix.py) already produce -- it
makes no legal or dimensional judgement of its own, so unlike those two
modules it has nothing to raise AmbiguousDimension about and nothing that
belongs in DECISIONS-NEEDED.md. It exists so `app/rulesets.py`'s binding gate
(CONTRACT.md §1 S8) and `GET /healthz` have one small, explicit file to read
rather than inferring "is this ruleset binding?" from the presence of files.

`binding` is fixed by ruleset_key, per CONTRACT.md §3.2 and the project's
CLAUDE.md ("Real applications run against the ADOPTED Code only"): the
`adopted` ruleset is the only binding one; every other ruleset_key (a CZC
draft, or a scratch/test ruleset) is non-binding. This mirrors
DB migration 0001's `rulesets.binding` column -- both must agree, since §1 S8
is enforced in both places.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "newcastle.ruleset-manifest/1.0.0"
BUILDER_VERSION = "ruleset_build/1.0.0"

# The one ruleset_key CONTRACT.md and the DB schema treat as binding.
BINDING_RULESET_KEYS = frozenset({"adopted"})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_manifest(
    ruleset_key: str,
    *,
    districts_path: Path,
    use_matrix_path: Path,
    source_paths: dict[str, Path],
    label: str | None = None,
    article_scheme: str = "adopted",
    adopted_on: str | None = None,
) -> dict[str, Any]:
    """Build the newcastle.ruleset-manifest/1.0.0 dict for `ruleset_key`.

    `districts_path` / `use_matrix_path` are the already-built sibling output
    files (this function does not build them; it only manifests them, and
    requires both to already exist on disk -- a manifest for a ruleset whose
    districts.json/use-matrix.json are missing or stale would be a false
    claim about what that ruleset directory actually contains).
    `source_paths` is a name -> Path map (e.g. {"source/article-02-data.json":
    Path(...), "source/article-02.typ": Path(...)}) hashed into
    `source_sha256` for provenance/reproducibility (CONTRACT.md §4.5 example).
    """
    if not districts_path.exists():
        raise FileNotFoundError(f"districts.json not found: {districts_path}")
    if not use_matrix_path.exists():
        raise FileNotFoundError(f"use-matrix.json not found: {use_matrix_path}")

    return {
        "schema": SCHEMA,
        "ruleset_key": ruleset_key,
        "label": label or f"Newcastle Core Zoning Code ({ruleset_key})",
        "binding": ruleset_key in BINDING_RULESET_KEYS,
        "article_scheme": article_scheme,
        "adopted_on": adopted_on,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builder_version": BUILDER_VERSION,
        "files": {"districts": "districts.json", "use_matrix": "use-matrix.json"},
        "source_sha256": {name: _sha256_file(p) for name, p in sorted(source_paths.items())},
    }
