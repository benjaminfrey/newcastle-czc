"""Amendments flag the entries that cite what they changed (design 2, §10).

The change list is section by section, from two rulesets' `articles.json`: any ruleset folder, a
draft's included, so a draft amendment can be checked before it goes to the Town. Flagged entries
are pulled only when the amendment is adopted and its ruleset pinned, never for a draft: until
then, the Code they explain is the one in force.
"""

import json
import re
from datetime import date
from pathlib import Path

from .model import Library
from .write import dump_batch, read_batch

AMENDMENT = "the amendment check"
_ID = re.compile(r"^[^:]+:a(\d+)\.s([^.]+)\.(.+)$")


def section_texts(root: Path) -> dict[str, str]:
    """Every node of a ruleset folder's articles, by citation ("5.7.c.3"), with its text."""
    out = {}
    for n in json.loads((root / "articles.json").read_text())["nodes"]:
        m = _ID.match(n["id"])
        if m:
            out[f"{m[1]}.{m[2]}.{m[3]}"] = n["text"]
    return out


def changed(old: dict[str, str], new: dict[str, str]) -> frozenset[str]:
    return frozenset(r for r in old.keys() | new.keys() if old.get(r) != new.get(r))


def _touches(cite: str, changes: frozenset[str]) -> bool:
    return any(c == cite or c.startswith(cite + ".") for c in changes)


def flagged(lib: Library, changes: frozenset[str]) -> list[tuple[str, tuple[str, ...]]]:
    """(entry id, its cites that changed), for entries not already pulled, in id order."""
    out = []
    for e in sorted(lib.entries.values(), key=lambda e: e.id):
        hit = tuple(c for c in e.cites if _touches(c, changes))
        if hit and e.status != "pulled":
            out.append((e.id, hit))
    return out


def flag(root: Path, old: Path, new: Path, *, apply: bool, on: date | None = None) -> list[list]:
    """The entries under `root` that cite what changed between two ruleset folders; with `apply`,
    pulled (an approved one) until re-approved and re-ratified."""
    from .load import load_library
    changes = changed(section_texts(old), section_texts(new))
    hits = flagged(load_library(root), changes)
    if apply and hits:
        ids = dict(hits)
        for path in sorted(root.glob("*.yaml")):
            entries, questions = read_batch(path)
            touched = False
            for e in entries:
                if e["id"] in ids and e["status"] != "draft":
                    e.update(status="pulled", pulled_on=on or date.today(), pulled_by=AMENDMENT,
                             pulled_why=f"Amended: {', '.join(ids[e['id']])}")
                    touched = True
            if touched:
                dump_batch(path, entries, questions)
    return [[i, list(c)] for i, c in hits]
