#!/usr/bin/env python3
"""Version-string rules for the CZC release lifecycle.

  vX.Y-draft   a draft            (decimal, -draft suffix)
  vN.0         adopted law        (whole number, no suffix)

"A whole number means adopted law" is only worth something if it cannot be
faked, so this is a refusal rather than a convention (ADOPTION-SPEC.md §6.1).
v0.1-baseline is deliberately NOT an adoption version: it is a transcription of
the previously adopted Code, not an adoption this tool produced.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

# A third component is part of this repo's real history -- v0.2.1-draft and
# v0.4.1 through v0.4.5-draft are shipped tags -- so the grammar accepts it.
# It is NOT laxity: an adoption version must still be exactly vN.0 with no
# patch component and no suffix (is_adoption_version below), and anything
# outside this grammar is now refused rather than waved through.
_RE = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?(?:-(draft|baseline))?$")


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    is_draft: bool
    suffix: str | None
    patch: int | None = None


def parse(v: str) -> Version:
    m = _RE.match(v.strip())
    if not m:
        raise ValueError(
            f"{v!r} is not a recognised version (expected vX.Y[.Z][-draft])")
    return Version(int(m.group(1)), int(m.group(2)),
                   m.group(4) == "draft", m.group(4),
                   int(m.group(3)) if m.group(3) is not None else None)


def is_adoption_version(v: str) -> bool:
    try:
        p = parse(v)
    except ValueError:
        return False
    return (p.minor == 0 and p.patch is None and p.suffix is None
            and p.major >= 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require", choices=("adoption", "draft"), required=True)
    ap.add_argument("version")
    a = ap.parse_args()
    if a.require == "adoption":
        if not is_adoption_version(a.version):
            print(f"{a.version!r} is not an adoption version. An adoption must "
                  f"carry a WHOLE number (v1.0, v2.0) with no suffix — a whole "
                  f"number means adopted law.", file=sys.stderr)
            return 1
    else:
        # Parse FIRST, and refuse on failure. is_adoption_version() swallows a
        # ValueError and returns False, so a malformed version used to sail
        # through this branch: `--require draft vX.Y.Z-frozen` exited 0 with no
        # message. That is parsing that fails OPEN on the one command whose job
        # is to refuse, and it silently widened what could be stamped onto a
        # legal instrument. The --require adoption branch never had the hole
        # (it demands a positive match); this makes both directions symmetric.
        # (Found in the Task 6 review, fixed in the final whole-branch pass.)
        try:
            parse(a.version)
        except ValueError as exc:
            print(f"{exc} — refusing rather than accepting an unrecognised "
                  f"version string for a release.", file=sys.stderr)
            return 1
        if is_adoption_version(a.version):
            print(f"{a.version!r} is a whole number, which is reserved for adopted "
                  f"law. Use a decimal draft version (v1.1-draft).", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
