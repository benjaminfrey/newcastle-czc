#!/usr/bin/env python3
"""The substantive-change determination: which Articles changed in substance
between two versions of the Code.

WHY. Standing rule 4 ships a standalone document and a standalone redline for
every Article with "changes to that Article's own standards, definitions or
data". Until this module the only instrument was adoption_breakdown.py, which
counts markdown lines only -- and so reported Article 2 at ZERO across
v0.24-draft -> v1.0, a release whose district data changed in eleven districts
and one use cell. That false zero shipped. This module reads the prose AND
every data source the ownership map (build/article-manifest.json) declares.

WHAT IT REPORTS, per Article -- four independent counts and a proposed verdict:
  prose    changed prose lines (frontmatter, HTML comments, blank lines,
           headings and raw-Typst blocks are not prose)
  heading  changed heading lines -- the redline can never mark a heading, so
           this is the only place an added, deleted or retitled section shows
  table    changed raw-Typst table blocks, which the redline renders unmarked
  data     changed leaves of the Article's json-keyed data sources, keyed by
           record, so a re-extracted or re-indented file is not a change
plus `suppressed` (section renumbers Rule 6 suppressed, given a section map)
and `needs_call` (files a machine cannot judge: layout units, binary exhibits,
and a generated file that changed while its source did not).

Every count uses the one counting rule (normalize_for_diff.marked_lines): a
modified line counts twice, once out and once in.

VERDICT -- proposed, never final; the release driver records any override:
  SUBSTANTIVE    any of prose / heading / table / data is nonzero
  NEEDS-CALL     none of those, but a file needs a person's call
  RENUMBER-ONLY  none of those, but section references were renumbered
  UNCHANGED      nothing
A retargeted cross-reference is never renumber-only (decision D8): Rule 6
rewrites a reference only to the number of a title-identical section, so a
retarget still differs and counts as prose.

IT REFUSES (exit 1) rather than guess when: a changed file is claimed by no
Article, or by two; a changed file is listed as shared (ruled by Ben Frey,
2026-10-09 -- what a shared change implies is undecided, so a person must say
which Articles it affects); a key is not unique; a JSON file does not parse; a
compare or key form is unknown; a ref does not exist; a section map fails its
self-check.

The ownership map is read from the WORKING TREE for both sides: it is this
instrument's configuration, not part of the Code's history (v1.0's own
manifest predates data_sources).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent
SOURCE = REPO / "source"
sys.path.insert(0, str(BUILD))

import manifest  # noqa: E402


class Refusal(Exception):
    """The determination cannot be made honestly. Exit 1, nothing written."""


# --- The keyed comparator. use_table_changes.py imports it; there is one. ----

def keyed_records(data, key: str) -> dict[str, object]:
    """The records of one json-keyed data source, keyed per its manifest `key`.

    The manifest leaves the key grammar to its consumer. The forms are:
      "$top-level-keys-except-_meta"  an object keyed by name, minus _meta
      "[].f1+f2"                      a bare list of records, keyed by f1 + f2
      "name[].f"                      the list under data["name"], keyed by f
    A record key is its field values joined with " / ". Refuses an unknown
    form, a record missing a key field, or a key that is not unique: a
    colliding key would silently merge two records into one.
    """
    if key == "$top-level-keys-except-_meta":
        if not isinstance(data, dict):
            raise Refusal(f"key {key!r} needs a JSON object, found {type(data).__name__}")
        return {str(k): v for k, v in data.items() if k != "_meta"}
    m = re.fullmatch(r"(\w*)\[\]\.(\w+(?:\+\w+)*)", key)
    if not m:
        raise Refusal(f"unknown key form {key!r}")
    container, fields = m.group(1), m.group(2).split("+")
    if container:
        records = data.get(container) if isinstance(data, dict) else None
    else:
        records = data
    if not isinstance(records, list):
        raise Refusal(f"key {key!r} needs a list of records, found {type(records).__name__}")
    out: dict[str, object] = {}
    for rec in records:
        if not isinstance(rec, dict) or any(f not in rec for f in fields):
            raise Refusal(f"key {key!r}: a record has no {'+'.join(fields)}")
        k = " / ".join(str(rec[f]) for f in fields)
        if k in out:
            raise Refusal(f"key {key!r} is not unique: {k!r} appears twice -- "
                          f"two records would be merged into one")
        out[k] = rec
    return out


def _list_keys(items: list) -> tuple[list[str], str]:
    """How to key the items of one list: by title, by label, or by position."""
    if all(isinstance(i, dict) and isinstance(i.get("title"), str) for i in items):
        seen: Counter = Counter()
        keys = []
        for i in items:
            seen[i["title"]] += 1
            n = seen[i["title"]]
            keys.append(i["title"] if n == 1 else f"{i['title']} [{n}]")
        return keys, "title"
    if all(isinstance(i, list) and len(i) >= 2 and isinstance(i[0], str) for i in items):
        firsts = [i[0] for i in items]
        if len(set(firsts)) == len(firsts):
            return firsts, "label"
    return [f"[{n}]" for n in range(len(items))], "index"


def flatten(value, prefix: tuple = ()) -> dict[tuple, object]:
    """Every leaf of `value`, keyed by a path that survives an insertion where
    it can: a dict by its keys; a list of titled dicts by title (a repeated
    title gets " [2]"); a list of [label, ...] rows with distinct labels by
    label; any other list by position. An empty dict or list is itself a leaf,
    so emptying one is a change."""
    if isinstance(value, dict):
        if not value:
            return {prefix: {}}
        out: dict[tuple, object] = {}
        for k, v in value.items():
            out.update(flatten(v, prefix + (str(k),)))
        return out
    if isinstance(value, list):
        if not value:
            return {prefix: []}
        keys, how = _list_keys(value)
        out = {}
        for k, item in zip(keys, value):
            if how == "title":
                item = {f: v for f, v in item.items() if f != "title"}
            elif how == "label":
                item = item[1] if len(item) == 2 else item[1:]
            out.update(flatten(item, prefix + (k,)))
        return out
    return {prefix: value}


@dataclass
class Delta:
    """What changed between two leaf maps."""
    changed: dict = field(default_factory=dict)   # path -> (old, new)
    added: dict = field(default_factory=dict)     # path -> new
    removed: dict = field(default_factory=dict)   # path -> old

    def count(self) -> int:
        return len(self.changed) + len(self.added) + len(self.removed)


def diff_maps(old: dict, new: dict) -> Delta:
    """The one keyed comparator. Order: the new side's, then removals in the old side's."""
    d = Delta()
    for k, v in new.items():
        if k not in old:
            d.added[k] = v
        elif old[k] != v:
            d.changed[k] = (old[k], v)
    for k, v in old.items():
        if k not in new:
            d.removed[k] = v
    return d


def json_leaves(raw: bytes | None, decl: dict) -> dict[tuple, object]:
    """The leaves of one json-keyed data source, each path starting with its
    record key. Restricted to the declaration's substantive_fields when it
    names them (decision D7: derived fields are not substance). An absent file
    has no leaves, so adding or deleting one counts every leaf."""
    if raw is None:
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise Refusal(f"{decl.get('path')}: not valid JSON ({exc})") from exc
    fields = decl.get("substantive_fields")
    out: dict[tuple, object] = {}
    for rk, rec in keyed_records(data, decl["key"]).items():
        if fields is not None and isinstance(rec, dict):
            rec = {f: rec[f] for f in fields if f in rec}
        out.update(flatten(rec, (rk,)))
    return out


def leaf_label(path: tuple) -> str:
    """A leaf path as one readable string."""
    return " › ".join(path)
