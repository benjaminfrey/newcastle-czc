"""CLI entry point: lift the use matrix out of source/article-02*.{json,typ}
and write rulesets/<ruleset_key>/use-matrix.json.

This is a thin shim over ruleset_build.build_use_matrix — same pattern as
build/build-article-3.sh being a shim over build-standalone.sh in the main
repo: the logic (parsing, merging, validating) lives in legend.py and
build_use_matrix.py per CONTRACT.md §2's directory layout; this script is
just the runnable entry point + the atomic-write step.

Usage:
    python -m ruleset_build.lift_use_matrix [--ruleset-key adopted]

NOTE ON RULESET KEY: CONTRACT.md (this app's normative contract) names the
adopted ruleset "adopted" throughout — §4's schemas, §4.5's manifest example,
the DDL's example manifest_path ('rulesets/adopted/manifest.json'), and every
open item in DECISIONS-NEEDED.md all key off "adopted". The task brief that
commissioned this script named a different ruleset_key/output path
("czc-adopted-2020-11-03"); this script follows CONTRACT.md's established
"adopted" instead, to stay consistent with the rest of the app (districts.json
will presumably build to the same rulesets/adopted/ directory). Flag this for
Ben/the orchestrator to reconcile if the other name was actually intended —
--ruleset-key overrides it for a one-off rebuild under a different key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent

sys.path.insert(0, str(APP_ROOT))  # so `ruleset_build.*` imports work when run as a script

from ruleset_build.build_use_matrix import build_use_matrix  # noqa: E402

DEFAULT_RULESET_KEY = "adopted"
DEFAULT_SRC = REPO_ROOT / "source" / "article-02-data.json"
DEFAULT_LEGEND_TYP = REPO_ROOT / "source" / "article-02.typ"


def _atomic_write_json(target: Path, obj: dict) -> None:
    """CONTRACT.md §1.1 S2: validate-all-then-write, atomic temp+fsync+replace.
    (No backup step here — this is build OUTPUT regenerated from repo source,
    not a human-edited durable file like overrides/*.json.)
    """
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
            pass  # best-effort directory fsync
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset-key", default=DEFAULT_RULESET_KEY)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--legend-typ", type=Path, default=DEFAULT_LEGEND_TYP)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="defaults to rulesets/<ruleset-key>/use-matrix.json under APP_ROOT",
    )
    args = parser.parse_args(argv)

    out = args.out or (APP_ROOT / "rulesets" / args.ruleset_key / "use-matrix.json")

    matrix = build_use_matrix(args.src, args.legend_typ, args.ruleset_key)
    _atomic_write_json(out, matrix)

    counts = matrix["counts"]
    print(f"wrote {out.relative_to(APP_ROOT)}")
    print(f"  districts: {counts['districts']}  uses: {counts['uses']}  cells: {counts['cells']}")
    print(f"  by_code: {counts['by_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
