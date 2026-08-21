"""CLI entry point: lift the districts out of source/article-02-data.json and
write rulesets/<ruleset_key>/districts.json.

This is a thin shim over ruleset_build.build_districts — same pattern as
ruleset_build/lift_use_matrix.py over build_use_matrix.py: the logic
(panel/dimension normalization) lives in build_districts.py per CONTRACT.md
§2's directory layout; this script is just the runnable entry point + the
atomic-write step.

Usage:
    python -m ruleset_build.lift_districts [--ruleset-key adopted]

FAILS LOUDLY, ON PURPOSE, RIGHT NOW: as of this writing overrides/
dimension-qualifiers.json has two unresolved entries (sd-historic and
sd-marine, both "Frontage Zone Setback" = unqualified "20 ft" — see
DECISIONS-NEEDED.md D-0001/D-0002). Running this script raises
AmbiguousDimension and writes no districts.json until a human fills in
overrides/dimension-qualifiers.json. That is the CONTRACT.md §4.2.3/§7.4
behaviour, not a bug in this script.

NOTE ON RULESET KEY: see ruleset_build/lift_use_matrix.py's docstring — this
app's CONTRACT.md names the adopted ruleset "adopted" throughout, not the
"czc-adopted-2020-11-03" the task brief mentioned; this script follows
CONTRACT.md to stay consistent with rulesets/adopted/use-matrix.json.
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

from ruleset_build.build_districts import AmbiguousDimension, build_districts  # noqa: E402

DEFAULT_RULESET_KEY = "adopted"
DEFAULT_SRC = REPO_ROOT / "source" / "article-02-data.json"
DEFAULT_OVERRIDES = APP_ROOT / "overrides" / "dimension-qualifiers.json"


def _atomic_write_json(target: Path, obj: dict) -> None:
    """CONTRACT.md §1.1 S2: validate-all-then-write, atomic temp+fsync+replace."""
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
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="defaults to rulesets/<ruleset-key>/districts.json under APP_ROOT",
    )
    args = parser.parse_args(argv)

    out = args.out or (APP_ROOT / "rulesets" / args.ruleset_key / "districts.json")

    try:
        doc = build_districts(args.src, args.overrides, args.ruleset_key)
    except AmbiguousDimension as exc:
        print(f"AmbiguousDimension: {exc}", file=sys.stderr)
        print(
            "No districts.json written. Logged (or confirmed already logged) in "
            "DECISIONS-NEEDED.md. Resolve in overrides/dimension-qualifiers.json and re-run.",
            file=sys.stderr,
        )
        return 1

    _atomic_write_json(out, doc)

    counts = doc["counts"]
    print(f"wrote {out.relative_to(APP_ROOT)}")
    print(
        f"  districts: {counts['districts']}  dimensions: {counts['dimensions']}  "
        f"unresolved: {counts['unresolved']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
