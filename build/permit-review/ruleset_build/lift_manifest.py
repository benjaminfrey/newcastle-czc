"""CLI entry point: write rulesets/<ruleset_key>/manifest.json from the
already-built districts.json + use-matrix.json siblings.

Thin shim over ruleset_build.build_manifest, same atomic-write pattern as
lift_districts.py / lift_use_matrix.py. Run this LAST, after both
lift_districts.py and lift_use_matrix.py have succeeded -- it refuses to run
otherwise (a manifest can't truthfully describe files that don't exist yet).

Usage:
    python -m ruleset_build.lift_manifest [--ruleset-key adopted]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent

sys.path.insert(0, str(APP_ROOT))

from ruleset_build.build_manifest import build_manifest  # noqa: E402

DEFAULT_RULESET_KEY = "adopted"
DEFAULT_SOURCES = {
    "source/article-02-data.json": REPO_ROOT / "source" / "article-02-data.json",
    "source/article-02.typ": REPO_ROOT / "source" / "article-02.typ",
}


def _atomic_write_json(target: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError("round-trip verification failed before write — refusing to write")

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
            pass
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset-key", default=DEFAULT_RULESET_KEY)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    base = APP_ROOT / "rulesets" / args.ruleset_key
    districts_path = base / "districts.json"
    use_matrix_path = base / "use-matrix.json"
    out = args.out or (base / "manifest.json")

    try:
        doc = build_manifest(
            args.ruleset_key,
            districts_path=districts_path,
            use_matrix_path=use_matrix_path,
            source_paths=DEFAULT_SOURCES,
        )
    except FileNotFoundError as exc:
        print(f"cannot build manifest.json yet: {exc}", file=sys.stderr)
        print(
            "Run lift_districts.py and lift_use_matrix.py first (districts.json "
            "is blocked until DECISIONS-NEEDED.md's open blocking items are "
            "resolved -- see overrides/dimension-qualifiers.json).",
            file=sys.stderr,
        )
        return 1

    _atomic_write_json(out, doc)
    print(f"wrote {out.relative_to(APP_ROOT)}  binding={doc['binding']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
