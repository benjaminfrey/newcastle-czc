#!/usr/bin/env python3
"""Assert that adoption-map.json has been rolled over after an adoption.

THE INVARIANT: comparing the baseline version against ITSELF must mark zero
lines. If the map is correct, an article's baseline text normalised as the
old side is identical to that same text taken verbatim as the new side, so
the redline has nothing to mark. Any nonzero count is the map rewriting text
that did not change.

WHY THIS EXISTS. After v1.0 is adopted it becomes the previously adopted
version for the next cycle, and adoption-map.json must be reset (spec §3.1):
baseline_version to the new adoption, article_numbers and files to identity,
and the new-at-this-adoption and not-text-comparable entries cleared. Nothing
performs that edit -- it is done by hand, once, possibly years later, by
someone who has no reason to suspect the file.

Getting it HALF right is the danger, because the halves fail differently:

  - files left stale FAILS LOUDLY. adoption_breakdown.py already refuses with
    "points at 'article-03-site-standards.md', which does not exist at v1.0."
    Nothing builds. That half needs no help.

  - article_numbers left stale FAILS SILENTLY. Measured 2026-08-25 against the
    real v1.0 tree: baseline_version and files corrected but the renumbering
    map left at 3->4...8->9 reports 308 substantive changed lines comparing
    v1.0 to itself, and exits 0. The old side's "Article 4" is rewritten to
    "Article 5" against a new side that says "Article 4". That is a warrant
    packet full of changes nobody made, with no error anywhere.

  - not_text_comparable and the null file entries also fail silently: Article 2
    would render unmarked at every future meeting and Article 3 would be marked
    "NEW at this adoption" forever.

DORMANT UNTIL IT MATTERS. The check runs only when baseline_version is an
adoption version (a whole number). The present baseline, v0.1-baseline, is
deliberately not one: it is the 2020 Code in its own formatting conventions,
so normalising it legitimately changes it and a self-comparison there is
meaningless. So this is inert today and arms itself the moment the rollover
happens -- which is exactly when the mistake it catches becomes possible.
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "build"))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402
import version_state  # noqa: E402


def _baseline_text(version: str, basename: str) -> str | None:
    r = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{version}:source/{basename}"],
        capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def problems(amap) -> list[str]:
    """Everything wrong with the map, as operator-readable lines. Empty == clean.

    Returns [] without checking anything when the baseline is not an adoption
    version -- see the module docstring.
    """
    out: list[str] = []
    for current, base in sorted(amap.files.items()):
        if base is None:
            out.append(
                f"{current}: still marked new at this adoption (null in `files`). "
                f"After an adoption nothing is new -- set it to itself.")
            continue
        reason = amap.not_text_comparable_reason(current)
        if reason:
            out.append(
                f"{current}: still listed in `not_text_comparable`. After an "
                f"adoption both sides are the same format, so it would render "
                f"unmarked at every future meeting, hiding real changes.")
            continue
        text = _baseline_text(amap.baseline_version, base)
        if text is None:
            out.append(
                f"{current}: `files` points at {base!r}, which does not exist "
                f"at {amap.baseline_version}. Reset `files` to identity.")
            continue
        n = nz.changed_line_count(text, text, amap=amap)
        if n:
            out.append(
                f"{current}: {n} phantom changed line(s) comparing "
                f"{amap.baseline_version} against itself. The map is rewriting "
                f"text that did not change -- check `article_numbers`.")
    return out


def run(map_path: str | None = None) -> int:
    amap = adoption_map.load(map_path)
    if not version_state.is_adoption_version(amap.baseline_version):
        print(f"[baseline] {amap.baseline_version} is not an adoption version — "
              f"self-check skipped (see build/baseline_selfcheck.py).")
        return 0
    found = problems(amap)
    if not found:
        print(f"[baseline] {amap.baseline_version} vs itself: 0 marked lines — "
              f"adoption-map.json is correctly rolled over.")
        return 0
    print(f"adoption-map.json has not been rolled over for "
          f"{amap.baseline_version}:", file=sys.stderr)
    for p in found:
        print(f"  - {p}", file=sys.stderr)
    print("\nAfter an adoption the map resets (spec §3.1): baseline_version to the "
          "new adoption,\narticle_numbers and files to identity, "
          "new_at_this_adoption and not_text_comparable\nemptied. Fix it before "
          "building a packet against this baseline.", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--map", default=None,
                    help="override adoption-map.json path (testing only)")
    return run(ap.parse_args().map)


if __name__ == "__main__":
    raise SystemExit(main())
