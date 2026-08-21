"""W2 orchestrator: runs the whole offline ruleset build as ONE pipeline.

    python -m ruleset_build.build_ruleset [--skip-citations] [--actor-user-id ID]

Steps, in order (each step reuses the existing, already-tested builder for
that piece -- this module does no parsing/extraction of its own):

    1. parse the DRAFT CZC          -> ruleset_build.parse_articles.main()
                                        ruleset_build.parse_definitions.main()
                                        writes rulesets/draft-v0.22/{articles,uses,definitions}.json
    2. extract the ADOPTED Code     -> ruleset_build.extract_adopted.main()
                                        writes rulesets/adopted/articles.json
       + adopted use-matrix         -> ruleset_build.lift_use_matrix.main()
                                        writes rulesets/adopted/use-matrix.json
       (rulesets/adopted/districts.json is DELIBERATELY never built here --
       blocked on DECISIONS-NEEDED.md D-0001/D-0002. See the module docstring
       note below and CONTRACT.md §4.2.3/§4.2.4. Nothing in this file may
       create it, work around its absence, or guess at it.)
    3. article-map + crosswalk      -> ruleset_build.crosswalk.main()
                                        writes rulesets/{article-map,crosswalk,crosswalk-overrides}.json
    4. a manifest.json per ruleset  -> _build_manifest() below, written to
                                        rulesets/<key>/manifest.json
    5. register both rulesets       -> _register_ruleset() below, upserted
       in the app DB (rulesets table)  into app/migrations/0001_init.sql's
                                        `rulesets` table, one events row per
                                        upsert (CONTRACT.md §3.3)
    6. (optional, default on) run ruleset_build.verify_citations against the
       real adopted ruleset and print its "CITATIONS: x/y resolved" line --
       informational only; a citation gap never fails this pipeline (fixing
       gaps is extractor work, tracked separately, per the W2 task brief:
       "iterate on the extractors, not the gate").

Idempotent: re-running regenerates the same build outputs from the same
repo source (byte-identical, since every builder step is a pure function of
its source files) and UPSERTS (never duplicates) each ruleset's DB row,
keyed on the UNIQUE `rulesets.ruleset_key` column -- the row's `id` and
`created_at` are preserved across re-runs; only the build-derived columns
(`built_at`, `source_sha_json`, `manifest_path`, ...) refresh.

MANIFEST SCHEMA NOTE: CONTRACT.md §4.5 defines manifest.json for the
Phase-1 two-file shape (districts.json + use-matrix.json) that
`ruleset_build/build_manifest.py` + `lift_manifest.py` already implement
verbatim, and that script is left untouched here -- it will simply start
working once districts.json exists (D-0001/D-0002 resolved). W2 needs a
manifest for BOTH rulesets built here, whose actual file sets don't match
that fixed two-file shape (adopted: articles.json + use-matrix.json, no
districts.json; draft: articles.json + definitions.json + uses.json), so
_build_manifest() below is a generalized sibling: same spirit (pure
metadata over already-built sibling files, §4.5's binding/article_scheme/
adopted_on/built_at/builder_version/source_sha256 fields all present and
meaning the same thing), extended with the field set W2's task brief asked
for by name (id, title, kind, status, adopted_date, content_sha256, counts)
and a `files` dict that lists only what actually exists for that ruleset --
it never claims a file is present that isn't.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))  # so `ruleset_build.*` / `app.*` imports work when run as a script

from ruleset_build import crosswalk as _crosswalk  # noqa: E402
from ruleset_build import extract_adopted as _extract_adopted  # noqa: E402
from ruleset_build import lift_use_matrix as _lift_use_matrix  # noqa: E402
from ruleset_build import parse_articles as _parse_articles  # noqa: E402
from ruleset_build import parse_definitions as _parse_definitions  # noqa: E402

MANIFEST_SCHEMA = "newcastle.ruleset-manifest/1.1.0"
BUILDER_VERSION = "ruleset_build/2.0.0"  # W2: adds build_ruleset.py orchestration + generalized manifests

# The adopted Code's own "Adopted: November 3, 2020" footer, present on
# every content page of docs/Newcastle Core Zoning Code.pdf (verified by
# scanning all pages -- a single, consistent date, never guessed).
ADOPTED_ON = "2020-11-03"


# --------------------------------------------------------------------------- #
# Small shared helpers (same atomic-write / sha256 pattern used throughout
# ruleset_build/ -- see lift_use_matrix.py, crosswalk.py, extract_adopted.py)
# --------------------------------------------------------------------------- #


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(target: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError(f"round-trip verification failed before write — refusing to write {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f"{target.name}.tmp-{os.getpid()}-{os.urandom(3).hex()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        try:
            dir_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # best-effort directory fsync
    finally:
        if tmp.exists():
            tmp.unlink()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Step 1 — parse the draft CZC
# --------------------------------------------------------------------------- #


def step_parse_draft(ruleset_key: str = "draft-v0.22") -> None:
    print(f"[1/6] parsing DRAFT CZC ({ruleset_key}) from source/article-0N-*.md ...")
    rc = _parse_articles.main(["--ruleset-key", ruleset_key])
    if rc != 0:
        raise RuntimeError(f"ruleset_build.parse_articles.main() exited {rc}")
    rc = _parse_definitions.main(["--ruleset-key", ruleset_key])
    if rc != 0:
        raise RuntimeError(f"ruleset_build.parse_definitions.main() exited {rc}")


# --------------------------------------------------------------------------- #
# Step 2 — extract the adopted Code (+ its use-matrix)
# --------------------------------------------------------------------------- #


def step_extract_adopted() -> None:
    print("[2/6] extracting the ADOPTED Code from docs/Newcastle Core Zoning Code.pdf ...")
    rc = _extract_adopted.main([])
    if rc != 0:
        raise RuntimeError(f"ruleset_build.extract_adopted.main() exited {rc}")
    rc = _lift_use_matrix.main([])
    if rc != 0:
        raise RuntimeError(f"ruleset_build.lift_use_matrix.main() exited {rc}")
    # districts.json is INTENTIONALLY not built here -- see module docstring
    # and CONTRACT.md §4.2.3/§4.2.4. DECISIONS-NEEDED.md D-0001/D-0002 stay
    # OPEN until a human resolves them in overrides/dimension-qualifiers.json.


# --------------------------------------------------------------------------- #
# Step 3 — article-map + crosswalk
# --------------------------------------------------------------------------- #


def step_build_crosswalk() -> None:
    print("[3/6] building article-map + crosswalk (adopted <-> draft numbering) ...")
    rc = _crosswalk.main([])
    if rc != 0:
        raise RuntimeError(f"ruleset_build.crosswalk.main() exited {rc}")


# --------------------------------------------------------------------------- #
# Step 4 — manifests
# --------------------------------------------------------------------------- #


def _file_counts(path: Path) -> Any:
    """Best-effort: return the built file's own top-level `counts` block, if
    it has one (every builder in this repo emits one). None if the file is
    absent or has no such block -- never raises, a manifest is metadata,
    not a second validator."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("counts") if isinstance(data, dict) else None


def _build_manifest(
    *,
    manifest_id: str,
    ruleset_key: str,
    kind: str,
    title: str,
    status: str,
    binding: bool,
    article_scheme: str,
    adopted_date: str | None,
    base_dir: Path,
    file_names: dict[str, str],  # logical name -> filename, e.g. {"articles": "articles.json"}
    source_paths: dict[str, Path],  # display name -> Path, hashed for provenance
) -> dict[str, Any]:
    """Builds the newcastle.ruleset-manifest/1.1.0 dict for one ruleset
    directory. See the module docstring's "MANIFEST SCHEMA NOTE" for why
    this is a generalized sibling of build_manifest.py's fixed two-file
    §4.5 shape rather than a reuse of it.

    Only files that actually EXIST are reported in `files`/`content_sha256`/
    `counts` -- a manifest never claims a file is present when it is not
    (most notably: `districts` is simply absent from all three for the
    `adopted` ruleset, honestly, rather than padded with a null placeholder
    that could be mistaken for "checked, and it's empty").
    """
    files: dict[str, str] = {}
    content_sha256: dict[str, str] = {}
    counts: dict[str, Any] = {}
    for logical_name, filename in file_names.items():
        p = base_dir / filename
        if not p.exists():
            continue
        files[logical_name] = filename
        content_sha256[logical_name] = _sha256_file(p)
        c = _file_counts(p)
        if c is not None:
            counts[logical_name] = c

    return {
        "schema": MANIFEST_SCHEMA,
        "id": manifest_id,
        "ruleset_key": ruleset_key,
        "kind": kind,
        "title": title,
        "label": title,  # CONTRACT.md §4.5's field name, kept as an alias for that consumer
        "status": status,
        "binding": binding,
        "article_scheme": article_scheme,
        "adopted_date": adopted_date,
        "adopted_on": adopted_date,  # CONTRACT.md §4.5's field name, kept as an alias
        "built_at": _utc_now_iso(),
        "builder_version": BUILDER_VERSION,
        "files": files,
        "content_sha256": content_sha256,
        "counts": counts,
        "source_sha256": {name: _sha256_file(p) for name, p in sorted(source_paths.items()) if p.exists()},
    }


def step_write_manifests(*, adopted_id: str, draft_id: str) -> tuple[dict, dict]:
    print("[4/6] writing manifest.json for both rulesets ...")

    adopted_manifest = _build_manifest(
        manifest_id=adopted_id,
        ruleset_key="adopted",
        kind="adopted-czc",
        title="Newcastle Core Zoning Code (Adopted)",
        status="active",
        binding=True,
        article_scheme="adopted",
        adopted_date=ADOPTED_ON,
        base_dir=APP_ROOT / "rulesets" / "adopted",
        file_names={"articles": "articles.json", "use_matrix": "use-matrix.json", "districts": "districts.json"},
        source_paths={"docs/Newcastle Core Zoning Code.pdf": REPO_ROOT / "docs" / "Newcastle Core Zoning Code.pdf"},
    )
    adopted_path = APP_ROOT / "rulesets" / "adopted" / "manifest.json"
    _atomic_write_json(adopted_path, adopted_manifest)
    print(f"  wrote {adopted_path.relative_to(APP_ROOT)}")

    draft_manifest = _build_manifest(
        manifest_id=draft_id,
        ruleset_key="draft-v0.22",
        kind="draft-czc",
        title="Newcastle Core Zoning Code (Draft v0.22)",
        status="draft",
        binding=False,
        article_scheme="draft",
        adopted_date=None,
        base_dir=APP_ROOT / "rulesets" / "draft-v0.22",
        file_names={"articles": "articles.json", "definitions": "definitions.json", "uses": "uses.json"},
        # source/ is a directory of article-0N-*.md files, not a single file
        # -- _build_manifest()'s source_paths hashes individual files, so
        # this is populated below (each article markdown file individually)
        # rather than passed here.
        source_paths={},
    )
    src_dir = REPO_ROOT / "source"
    draft_manifest["source_sha256"] = {
        f"source/{p.name}": _sha256_file(p) for p in sorted(src_dir.glob("article-0*.md"))
    }
    draft_path = APP_ROOT / "rulesets" / "draft-v0.22" / "manifest.json"
    _atomic_write_json(draft_path, draft_manifest)
    print(f"  wrote {draft_path.relative_to(APP_ROOT)}")

    return adopted_manifest, draft_manifest


# --------------------------------------------------------------------------- #
# Step 5 — register both rulesets in the DB (app/migrations/0001_init.sql's
# `rulesets` table). Upsert keyed on the UNIQUE ruleset_key column.
# --------------------------------------------------------------------------- #


def _register_ruleset(conn, manifest: dict[str, Any], *, manifest_path_rel: str,
                       is_current: bool, actor_user_id: str | None) -> str:
    """Upserts one row into `rulesets`, appends one `events` row in the same
    transaction (CONTRACT.md §3.3), and returns the row's id.

    `manifest["id"]` is the id this row will have (generated once by the
    caller, before the manifest is even written, so manifest.json's own
    `id` field and the DB row's `id` always agree -- see step_register()).
    On a re-run for an already-registered ruleset_key, the EXISTING row's
    `id` and `created_at` are preserved (only the build-derived columns
    refresh) -- so `manifest["id"]` passed in on a re-run is the id read
    back from that existing row, never a fresh uuid stepping on it.
    """
    ruleset_key = manifest["ruleset_key"]
    row_id = manifest["id"]
    now = _utc_now_iso()

    existing = conn.execute(
        "SELECT id, created_at FROM rulesets WHERE ruleset_key = ?;", (ruleset_key,)
    ).fetchone()

    source_sha_json = json.dumps(manifest["source_sha256"], sort_keys=True, ensure_ascii=False)

    if existing is not None:
        row_id = existing["id"]
        conn.execute(
            """
            UPDATE rulesets SET
                label = ?, binding = ?, article_scheme = ?, adopted_on = ?,
                built_at = ?, builder_version = ?, manifest_path = ?,
                source_sha_json = ?, is_current = ?, actor_user_id = ?
            WHERE id = ?;
            """,
            (
                manifest["title"], int(manifest["binding"]), manifest["article_scheme"],
                manifest["adopted_date"], manifest["built_at"], manifest["builder_version"],
                manifest_path_rel, source_sha_json, int(is_current), actor_user_id, row_id,
            ),
        )
        event_kind = "ruleset.updated"
    else:
        conn.execute(
            """
            INSERT INTO rulesets
                (id, ruleset_key, label, binding, article_scheme, adopted_on,
                 built_at, builder_version, manifest_path, source_sha_json,
                 is_current, superseded_by, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?);
            """,
            (
                row_id, ruleset_key, manifest["title"], int(manifest["binding"]),
                manifest["article_scheme"], manifest["adopted_date"], manifest["built_at"],
                manifest["builder_version"], manifest_path_rel, source_sha_json,
                int(is_current), now, actor_user_id,
            ),
        )
        event_kind = "ruleset.registered"

    from app.audit import append_event  # local import: keeps this module importable without app/ on a bare parse

    append_event(
        conn,
        actor_user_id=actor_user_id,
        kind=event_kind,
        payload={
            "ruleset_key": ruleset_key,
            "binding": bool(manifest["binding"]),
            "manifest_path": manifest_path_rel,
            "source_sha256": manifest["source_sha256"],
            "counts": manifest["counts"],
        },
        entity_table="rulesets",
        entity_id=row_id,
    )
    return row_id


def step_register(adopted_manifest: dict, draft_manifest: dict, *, actor_user_id: str | None = None) -> None:
    print("[5/6] registering both rulesets in the DB ...")
    from app.config import DB_PATH, MIGRATIONS_DIR
    from app.db import connect, migrate

    conn = connect(DB_PATH)
    try:
        migrate(conn, MIGRATIONS_DIR)
        conn.execute("BEGIN;")
        try:
            adopted_id = _register_ruleset(
                conn, adopted_manifest,
                manifest_path_rel="rulesets/adopted/manifest.json",
                is_current=True,  # the one binding, current adopted Code
                actor_user_id=actor_user_id,
            )
            draft_id = _register_ruleset(
                conn, draft_manifest,
                manifest_path_rel="rulesets/draft-v0.22/manifest.json",
                is_current=False,  # a draft can never be is_current (rulesets CHECK: is_current=0 OR binding=1)
                actor_user_id=actor_user_id,
            )
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        print(f"  adopted     -> rulesets.id={adopted_id}  binding=1  is_current=1")
        print(f"  draft-v0.22 -> rulesets.id={draft_id}  binding=0  is_current=0")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Step 6 — citation gate (informational)
# --------------------------------------------------------------------------- #


def step_verify_citations() -> None:
    print("[6/6] running the citation-verification harness against the adopted ruleset ...")
    from ruleset_build import verify_citations

    report = verify_citations.build_report()
    verify_citations.write_report(report, verify_citations.REPORT_PATH)
    verify_citations.print_summary(report)
    c = report["counts"]
    print()
    print(f"CITATIONS: {c['resolved']}/{c['gate_scope_total']} resolved ({c['resolved_pct']}%)")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _existing_or_new_id(ruleset_key: str) -> str:
    """Looks up an already-registered ruleset's id so a re-run's manifest.json
    and DB row agree on `id` instead of minting a fresh uuid every build
    (which would otherwise drift from the DB's stable row id on every
    rebuild). Falls back to a fresh uuid4 hex for a ruleset_key never seen
    before, or if the DB does not exist yet."""
    try:
        from app.config import DB_PATH, MIGRATIONS_DIR
        from app.db import connect, migrate

        if not DB_PATH.exists():
            return uuid.uuid4().hex
        conn = connect(DB_PATH)
        try:
            migrate(conn, MIGRATIONS_DIR)
            row = conn.execute(
                "SELECT id FROM rulesets WHERE ruleset_key = ?;", (ruleset_key,)
            ).fetchone()
            return row["id"] if row is not None else uuid.uuid4().hex
        finally:
            conn.close()
    except Exception:
        return uuid.uuid4().hex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-citations", action="store_true",
                         help="skip step 6 (the citation-verification report)")
    parser.add_argument("--actor-user-id", default=None,
                         help="actor_user_id recorded on the rulesets rows + events (default: system/NULL)")
    args = parser.parse_args(argv)

    step_parse_draft()
    step_extract_adopted()
    step_build_crosswalk()

    adopted_id = _existing_or_new_id("adopted")
    draft_id = _existing_or_new_id("draft-v0.22")
    adopted_manifest, draft_manifest = step_write_manifests(adopted_id=adopted_id, draft_id=draft_id)

    step_register(adopted_manifest, draft_manifest, actor_user_id=args.actor_user_id)

    if not args.skip_citations:
        step_verify_citations()

    print()
    print("build_ruleset: done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
