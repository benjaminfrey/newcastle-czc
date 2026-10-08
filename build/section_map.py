#!/usr/bin/env python3
"""Derive a SECTION renumbering map between two versions of the Code.

WHY THIS EXISTS. When a section is inserted into an Article -- Right to Farm
puts a new Section 3 into Article 7 -- every later section's number shifts, and
every heading and cross-reference to them changes by one. Those are not
amendments, but a raw diff counts each one, so the packet's headline number
would carry two phantom lines per shifted heading and reference.
normalize_for_diff.py suppresses them on the OLD side -- given a map saying
which old section became which new one. This module produces that map.

WHY IT IS DERIVED, NOT AUTHORED. A hand-maintained renumbering map is exactly
the failure baseline_selfcheck.py exists to catch: 308 phantom lines comparing
v1.0 to itself, exit 0. And this map cannot live in adoption-map.json anyway:
populating that file for the next amendment makes baseline_selfcheck refuse it
as "not rolled over". So the map is derived from the two trees, written to a
release's staging directory, and never committed. adoption-map.json,
adoption_map.py and baseline_selfcheck.py are NOT touched by this module.

WHAT COUNTS AS A RENUMBERING. Only a section whose `## N.` heading title is
identical (after normalising whitespace and case) in both versions, aligned in
order, with a different number. A retitled, added, deleted or ambiguous section
is NOT mapped -- it stays fully visible in the redline as a real change. That
conservatism is the point: a map that maps too much hides a real amendment, and
an omission from a redline is invisible to the reader.

SCOPE. `## N.` headings only (Articles 1-8; Article 9 has none). Lettered
`### x.` sub-sections are not mapped, so inserting a sub-section still shows
its shifted references as changes -- recoverable noise, never a hidden
amendment.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent
DEFAULT_NEW_DIR = REPO / "source"

# `## N. TITLE`. Measured 2026-10-08: every `## ` line in source/article-0*.md
# matches `^## [0-9]+\. ` -- digits, period, one space, uppercase title.
_H2 = re.compile(r"^## (\d+)\. (.+?)\s*$", re.MULTILINE)
_ARTICLE_NUMBER = re.compile(r'^article-number:\s*"(\d+)"', re.MULTILINE)

# Below this fraction of an Article's old headings found again in order, the
# alignment is too weak to trust as a pure renumbering, and derive() fails
# closed rather than guess. Inserting one section into Article 7 finds 66 of 66
# (1.0); a wholesale rewrite finds few. How an operator supplies a hand entry in
# that case is the release driver's decision, not this module's.
SIMILARITY_FLOOR = 0.5


class BelowFloor(Exception):
    """An Article's headings align too weakly to derive a map from."""


class NoComparison(Exception):
    """The comparison could not be made at all (bad ref, or nothing to compare)."""


def _git_show(ref: str, path: str) -> str | None:
    # Imported here rather than at module top: redline_resolve imports THIS
    # module to apply a map, so a top-level import would be circular.
    from redline_resolve import git_show
    return git_show(ref, path)


def normalise_title(title: str) -> str:
    return " ".join(title.split()).upper()


def headings(text: str) -> list[tuple[int, str]]:
    return [(int(m.group(1)), normalise_title(m.group(2))) for m in _H2.finditer(text)]


def article_number(text: str) -> int | None:
    m = _ARTICLE_NUMBER.search(text)
    return int(m.group(1)) if m else None


def derive_article(old_text: str, new_text: str):
    """Return (mapping, matched, old_unmatched, new_unmatched) for one Article.

    mapping       {old number: new number}, ONLY where the number changed for a
                  heading whose title is identical, unambiguous, and aligned in
                  order.
    matched       how many old headings were found again in order -- evidence
                  the derivation examined every heading, which a test of an
                  empty map needs (an empty map is also what a broken one gives).
    old_unmatched old headings left unmapped (retitled, deleted, reordered or
                  ambiguous): every reference to them stays visible as a change.
    new_unmatched new headings with no counterpart (added or retitled).
    """
    old_h, new_h = headings(old_text), headings(new_text)
    ambiguous = ({t for t, c in Counter(t for _, t in old_h).items() if c > 1}
                 | {t for t, c in Counter(t for _, t in new_h).items() if c > 1})
    sm = difflib.SequenceMatcher(None, [t for _, t in old_h], [t for _, t in new_h],
                                 autojunk=False)
    mapping: dict[int, int] = {}
    matched = 0
    old_unmatched: list[str] = []
    new_unmatched: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for (o_num, title), (n_num, _) in zip(old_h[i1:i2], new_h[j1:j2]):
                matched += 1
                if title in ambiguous:
                    old_unmatched.append(f"§{o_num} {title} (ambiguous title)")
                elif o_num != n_num:
                    mapping[o_num] = n_num
        else:
            old_unmatched += [f"§{n} {t}" for n, t in old_h[i1:i2]]
            new_unmatched += [f"§{n} {t}" for n, t in new_h[j1:j2]]
    return mapping, matched, old_unmatched, new_unmatched


def tree_hash(new_dir: Path) -> str:
    """Identify the tree a map was derived against, so it is not applied to another."""
    h = hashlib.sha256()
    for p in sorted(Path(new_dir).glob("article-0*.md")):
        h.update(p.name.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def derive(old_ref: str, new_dir: Path = DEFAULT_NEW_DIR) -> dict:
    new_dir = Path(new_dir)
    if subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet",
                       f"{old_ref}^{{commit}}"], capture_output=True).returncode != 0:
        raise NoComparison(f"{old_ref!r} is not a commit in this repository")
    doc: dict = {"for_old_ref": old_ref, "for_new_tree": tree_hash(new_dir),
                 "articles": {}, "matched": {}, "unmapped_old": {}, "unmapped_new": {},
                 "skipped": []}
    weak: list[str] = []
    for new_path in sorted(new_dir.glob("article-0*.md")):
        old_text = _git_show(old_ref, f"source/{new_path.name}")
        if old_text is None:
            # New at this version: nothing renumbered from it -- but visible.
            doc["skipped"].append(new_path.name)
            continue
        art = article_number(old_text)    # keyed on the OLD number, which references use
        if art is None:
            continue
        mapping, matched, old_un, new_un = derive_article(old_text, new_path.read_text())
        key = str(art)
        doc["matched"][key] = matched
        if old_un:
            doc["unmapped_old"][key] = old_un
        if new_un:
            doc["unmapped_new"][key] = new_un
        total = len(headings(old_text))
        if total and matched / total < SIMILARITY_FLOOR:
            weak.append(f"Article {art}: {matched} of {total} headings found again in order")
            continue
        if mapping:
            doc["articles"][key] = {str(o): n for o, n in sorted(mapping.items())}
    if not doc["matched"]:
        raise NoComparison(f"no article file in {new_dir} exists at {old_ref}; "
                           f"nothing was compared")
    if weak:
        raise BelowFloor("; ".join(weak))
    return doc


def load(path) -> dict[int, dict[int, int]]:
    doc = json.loads(Path(path).read_text())
    return {int(a): {int(o): int(n) for o, n in m.items()} for a, m in doc["articles"].items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("derive", help="derive a map from <old-ref> to a tree")
    d.add_argument("old_ref")
    d.add_argument("--new-dir", default=str(DEFAULT_NEW_DIR))
    d.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "derive":
        try:
            doc = derive(a.old_ref, Path(a.new_dir))
        except BelowFloor as exc:
            print(f"section_map: refusing to derive -- {exc}. Below the "
                  f"{SIMILARITY_FLOOR:.0%} similarity floor the alignment cannot be "
                  f"trusted as a pure renumbering; no map was written.", file=sys.stderr)
            return 2
        except NoComparison as exc:
            print(f"section_map: refusing to derive -- {exc}; no map was written.",
                  file=sys.stderr)
            return 1
        Path(a.out).write_text(json.dumps(doc, indent=2) + "\n")
        n = sum(len(m) for m in doc["articles"].values())
        print(f"section_map: {n} renumbered section(s) across "
              f"{len(doc['articles'])} Article(s) vs {a.old_ref}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
