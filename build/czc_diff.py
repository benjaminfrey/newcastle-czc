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
and a generated figure that changed although its source had no real data
change). A generated file is explained ONLY by a source with a nonzero data
change: a re-indented or _meta-only source changes its bytes, scores zero, and
so leaves the figure unexplained and in need of a person's call.

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

IT REFUSES (exit 1) rather than guess when:
  - a changed file is claimed by no Article, or by two Articles;
  - a changed file is listed as shared (ruled by Ben Frey, 2026-10-09 -- what a
    shared change implies is undecided, so a person must say which Articles it
    affects);
  - a changed file belongs to an Article number that is not in the manifest;
  - a record key is not unique, names a field a record lacks, or is of an
    unknown form (an unknown `compare` form refuses the same way);
  - a JSON file is broken, or holds a duplicate key in one object;
  - a declaration's substantive_fields is not a list of names, or names a field
    no record has (a misspelt field would make every change to it read as zero);
  - two leaves of one record share a path (one would hide the other);
  - a declaration has no key, or a generated-from entry has no source;
  - a ref does not exist;
  - --section-map is given with --new-ref (a map is checked against a tree), or
    the section map fails its self-check;
  - --article names an Article outside the manifest (every changed file is
    still classified first, so --article never narrows a refusal).
A refusal writes nothing, and removes any earlier --json file so a stale
answer cannot be mistaken for this run's.

The ownership map is read from the WORKING TREE for both sides: it is this
instrument's configuration, not part of the Code's history (v1.0's own
manifest predates data_sources).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent
SOURCE = REPO / "source"
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import manifest  # noqa: E402
import normalize_for_diff as nz  # noqa: E402
import structure_text  # noqa: E402


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
    # name[].f: only the records under `name` are compared. The container's
    # other keys (inventory.json's _meta: banner, CRS, town boundary) are not
    # the Code's standards and are deliberately not read.
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


def _merge(into: dict, more: dict) -> None:
    """Merge child leaves, refusing a shared path: a silent overwrite would let
    a change to the hidden leaf read as zero."""
    for path, v in more.items():
        if path in into:
            raise Refusal(f"two leaves share the path {leaf_label(path)!r} -- "
                          f"a change to one could be hidden by the other")
        into[path] = v


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
            _merge(out, flatten(v, prefix + (str(k),)))
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
            _merge(out, flatten(item, prefix + (k,)))
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
        elif type(old[k]) is not type(v) or old[k] != v:
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
    path = decl.get("path")
    if "key" not in decl:
        raise Refusal(f"{path}: json-keyed declaration has no key")
    fields = decl.get("substantive_fields")
    if fields is not None and not (isinstance(fields, list)
                                   and all(isinstance(f, str) for f in fields)):
        raise Refusal(f"{path}: substantive_fields must be a list of field names")
    if raw is None:
        return {}

    def no_dups(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                raise Refusal(f"{path}: duplicate key {k!r} in a JSON object -- "
                              f"one value would silently replace the other")
            seen.add(k)
        return dict(pairs)

    try:
        data = json.loads(raw, object_pairs_hook=no_dups)
    except ValueError as exc:
        raise Refusal(f"{path}: not valid JSON ({exc})") from exc
    records = keyed_records(data, decl["key"])
    if fields is not None:
        for name in fields:
            if not any(isinstance(r, dict) and name in r for r in records.values()):
                raise Refusal(f"{path}: substantive_fields names {name!r}, which no "
                              f"record has -- a misspelt field would make every "
                              f"change to it read as zero")
    out: dict[tuple, object] = {}
    for rk, rec in records.items():
        if fields is not None and isinstance(rec, dict):
            rec = {f: rec[f] for f in fields if f in rec}
        _merge(out, flatten(rec, (rk,)))
    return out


def leaf_label(path: tuple) -> str:
    """A leaf path as one readable string."""
    return " › ".join(path)


# --- The markdown counts ------------------------------------------------------

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_HEADING = re.compile(r"^\s*#{1,6}[ \t]")
_FM_KEY = re.compile(r"^[A-Za-z][\w-]*\s*:")
_FM_CONT = re.compile(r"^\s+\S")
_FM_ITEM = re.compile(r"^\s*-\s")
_FM_TITLE = re.compile(r"^(article-name|article-number)\s*:")


def _split_frontmatter(text: str) -> tuple[list[str], str]:
    """(frontmatter lines, body). Frontmatter exists only if the first line is
    `---` and every following line up to a closing `---` or `...` is a
    `key: value`, an indented continuation or a list item. Anything else before
    the closer (a blank line included), or no closer, means there is NO
    frontmatter and nothing is stripped -- so a stray `---` horizontal rule can
    never swallow prose."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return [], text
    for i in range(1, len(lines)):
        s = lines[i].rstrip()
        if s in ("---", "..."):
            return lines[1:i], "\n".join(lines[i + 1:])
        if not (_FM_KEY.match(s) or _FM_CONT.match(s) or _FM_ITEM.match(s)):
            return [], text
    return [], text


def split_markdown(text: str) -> tuple[list[str], list[str], list[str]]:
    """(prose lines, heading lines, raw blocks). Frontmatter, HTML comments,
    blank lines and trailing whitespace are removed; each fenced block is kept
    whole as one item, so an edit inside it is one changed block. The template
    prints an Article's title, tab and running head from the frontmatter keys
    `article-name` and `article-number`, so those two lines (stripped) lead the
    heading list; `footer-date` and every other key are page dressing and count
    nowhere."""
    fm, text = _split_frontmatter(text)
    fm_titles = [ln.strip() for ln in fm if _FM_TITLE.match(ln)]
    text = _COMMENT.sub("", text)
    lines = text.split("\n")
    prose: list[str] = []
    headings: list[str] = list(fm_titles)
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        m = _FENCE.match(lines[i])
        if m:
            close = re.compile(r"^[ \t]*" + re.escape(m.group(1)[0])
                               + "{" + str(len(m.group(1))) + r",}[ \t]*$")
            block = [lines[i]]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                i += 1
                if close.match(block[-1]):
                    break
            blocks.append("\n".join(block))
            continue
        line = lines[i].rstrip()
        i += 1
        if line.strip():
            (headings if _HEADING.match(line) else prose).append(line)
    return prose, headings, blocks


def _identity_amap():
    """The determination compares drafts and never renumbers Articles, so the
    old side's article map is identity. Built here, not read from
    adoption-map.json, which this module must not depend on."""
    return adoption_map.AdoptionMap(baseline_version="czc_diff",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})


def markdown_counts(old: str | None, new: str, *, smap=None) -> dict[str, int]:
    """prose / heading / table counts for one Article's markdown, and the
    section renumbers Rule 6 suppressed. The OLD side is normalised as
    the BASELINE redline's old side is (heading case, an identity article map,
    and Rule 6 when a section map is given); a draft-to-draft redline applies
    Rule 6 only, and the difference is heading-letter case, which the redline
    never marks anyway. The new side is read as written. `old` None means the
    Article is new."""
    if old is None:
        o_prose, o_heads, o_blocks, suppressed = [], [], [], 0
    else:
        suppressed = nz.section_renumber(old, smap)[1] if smap else 0
        o_prose, o_heads, o_blocks = split_markdown(
            nz.normalize_old_side(old, amap=_identity_amap(), smap=smap))
    n_prose, n_heads, n_blocks = split_markdown(new)
    return {"prose": nz.marked_lines(o_prose, n_prose),
            "heading": nz.marked_lines(o_heads, n_heads),
            "table": nz.marked_lines(o_blocks, n_blocks),
            "suppressed": suppressed}


_SECTION = re.compile(r"^\s*##[ \t]+(\d+[A-Za-z]?)\.[ \t]+(.*?)\s*(?:\{[^}]*\})?\s*$")
_SUBSECTION = re.compile(r"^\s*###[ \t]+([A-Za-z])\.[ \t]+(.*?)\s*(?:\{[^}]*\})?\s*$")


def _contextual_labels(heads: list[str]) -> list[str]:
    """One label per heading line, for the disclosure page. A sub-section
    ("### g. STREET TREES") alone does not say where it is, so it is labelled
    with the section above it ("Section 3.G -- STREET TREES"). The in-text notes
    use heading_label instead: they sit at the spot itself."""
    labels, section = [], None
    for h in heads:
        m = _SECTION.match(h)
        if m:
            section = m.group(1)
            labels.append(structure_text._clean(f"Section {section} \u2014 {m.group(2)}"))
            continue
        m = _SUBSECTION.match(h)
        if m and section is not None:
            labels.append(structure_text._clean(
                f"Section {section}.{m.group(1).upper()} \u2014 {m.group(2)}"))
            continue
        labels.append(structure_text.heading_label(h))
    return labels


def structural_changes(old: str | None, new: str, *, smap=None) -> dict[str, list]:
    """WHICH headings and raw-Typst tables/figures were added, removed or
    changed -- the names behind markdown_counts' heading and table counts. The
    old side is normalised exactly as in markdown_counts. Headings are labelled
    with their section (_contextual_labels). Tables and figures are classified
    by structure_text.classify_blocks, the one rule the redline's in-text notes
    share: identical content anywhere is unchanged, the rest pair by caption."""
    if old is None:
        o_heads, o_blocks = [], []
    else:
        _, o_heads, o_blocks = split_markdown(
            nz.normalize_old_side(old, amap=_identity_amap(), smap=smap))
    _, n_heads, n_blocks = split_markdown(new)
    out: dict[str, list] = {k: [] for k in ("headings_added", "headings_removed",
                                            "headings_changed", "tables_added",
                                            "tables_removed", "tables_changed")}
    o_labels, n_labels = _contextual_labels(o_heads), _contextual_labels(n_heads)
    hc = structure_text.classify_headings(o_heads, n_heads)
    out["headings_changed"] = [(o_labels[i], n_labels[j]) for i, j in hc["changed"]]
    out["headings_removed"] = [o_labels[i] for i in hc["removed"]]
    out["headings_added"] = [n_labels[j] for j in hc["added"]]
    o_caps = [structure_text.block_caption(b) for b in o_blocks]
    n_caps = [structure_text.block_caption(b) for b in n_blocks]
    cls = structure_text.classify_blocks(o_blocks, n_blocks)
    out["tables_changed"] = [n_caps[j] for _, j in sorted(cls["changed"], key=lambda p: p[1])]
    out["tables_removed"] = [o_caps[i] for i in cls["removed"]]
    out["tables_added"] = [n_caps[j] for j in cls["added"]]
    return out


# --- The two sides --------------------------------------------------------------

def _git(*args: str) -> str:
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(REPO), *args],
                          capture_output=True,
                          text=True, check=True).stdout


def _git_names(*args: str) -> list[str]:
    """Path names from a git listing run with `-z`: NUL-separated and never
    C-quoted, so a name holding a quote, a backslash or a control character is
    listed as it is. (core.quotePath=false covers only bytes above 0x80.)"""
    return [n for n in _git(*args).split("\0") if n]


class Side:
    """One version of source/: a git ref, or a directory."""

    def __init__(self, *, ref: str | None = None, root: Path | None = None):
        if (ref is None) == (root is None):
            raise ValueError("a Side is a ref or a directory, not both or neither")
        if ref is not None:
            ok = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet",
                                 f"{ref}^{{commit}}"], capture_output=True)
            if ok.returncode != 0:
                raise Refusal(f"{ref!r} is not a commit in this repository")
        self.ref = ref
        self.root = Path(root) if root is not None else None
        self.label = ref if ref is not None else str(self.root)
        self._cache: dict[str, bytes | None] = {}

    def files(self) -> list[str]:
        """Every file of the Code on this side, relative to source/."""
        if self.ref is not None:
            return sorted(p[len("source/"):] for p in
                          _git_names("ls-tree", "-r", "-z", "--name-only", self.ref, "source/"))
        if self.root.resolve() == SOURCE.resolve():
            # The live tree: what git tracks plus what it would track. Ignored
            # files (.DS_Store, inventory.json.bak-*) are not part of the Code.
            listed = set(_git_names("ls-files", "-z", "source/"))
            listed |= set(_git_names("ls-files", "-z", "--others", "--exclude-standard", "source/"))
            return sorted(p[len("source/"):] for p in listed if p and (REPO / p).is_file())
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*")
                      if p.is_file()
                      and not any(part.startswith(".") for part in p.relative_to(self.root).parts))

    def read(self, rel: str) -> bytes | None:
        """The file's bytes on this side, or None if it does not exist here."""
        if rel not in self._cache:
            if self.ref is not None:
                r = subprocess.run(["git", "-C", str(REPO), "show", f"{self.ref}:source/{rel}"],
                                   capture_output=True)
                self._cache[rel] = r.stdout if r.returncode == 0 else None
            else:
                p = self.root / rel
                self._cache[rel] = p.read_bytes() if p.is_file() else None
        return self._cache[rel]


# --- The determination ----------------------------------------------------------

@dataclass
class ArticleCounts:
    article: int
    prose: int = 0
    heading: int = 0
    table: int = 0
    data: int = 0
    suppressed: int = 0
    new: bool = False
    needs_call: list[str] = field(default_factory=list)
    data_detail: dict[str, Delta] = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        if self.prose or self.heading or self.table or self.data:
            return "SUBSTANTIVE"
        if self.needs_call:
            return "NEEDS-CALL"
        if self.suppressed:
            return "RENUMBER-ONLY"
        return "UNCHANGED"

    def as_json(self) -> dict:
        return {
            "prose": self.prose, "heading": self.heading, "table": self.table,
            "data": self.data, "suppressed": self.suppressed, "new": self.new,
            "verdict": self.verdict, "needs_call": self.needs_call,
            "data_detail": {
                path: {"changed": [{"path": leaf_label(k), "old": o, "new": n}
                                   for k, (o, n) in d.changed.items()],
                       "added": [{"path": leaf_label(k), "new": v} for k, v in d.added.items()],
                       "removed": [{"path": leaf_label(k), "old": v} for k, v in d.removed.items()]}
                for path, d in self.data_detail.items()},
        }


def _declaration(doc: dict, article: str, rel: str) -> dict | None:
    for d in doc.get(article, {}).get("data_sources", []):
        p = d.get("path", "")
        if (rel.startswith(p) if p.endswith("/") else rel == p):
            return d
    return None


def determine(old: Side, new: Side, *, doc: dict | None = None, smap=None) -> dict[int, ArticleCounts]:
    """Per-Article counts and a proposed verdict. Every changed file is
    classified through the ownership map BEFORE anything is counted, so a
    refusal is never preceded by a partial answer."""
    doc = manifest.load() if doc is None else doc
    result = {int(k): ArticleCounts(int(k)) for k in doc if k.isdigit()}
    changed = [p for p in sorted(set(old.files()) | set(new.files()))
               if old.read(p) != new.read(p)]

    owner: dict[str, str] = {}
    for p in changed:
        who = manifest.claimants(doc, p)
        if not who:
            raise Refusal(f"{p}: changed, and no Article claims it in build/article-manifest.json. "
                          f"Declare it in an Article's data_sources, or list it under ignored.")
        if len(who) > 1:
            raise Refusal(f"{p}: claimed by {', '.join(who)} -- the ownership map must name "
                          f"exactly one")
        if who[0] == "shared":
            raise Refusal(f"{p}: changed, and it is listed as shared. What a change to a shared "
                          f"file means for the determination is not decided, so a person must say "
                          f"which Articles it affects (ruled by Ben Frey, 2026-10-09).")
        if who[0] != "ignored":
            owner[p] = who[0]

    for p, art in owner.items():
        if int(art) not in result:
            raise Refusal(f"{p}: changed, and Article {art} is not in build/article-manifest.json")

    real_source_change: set[str] = set()      # json-keyed paths with a nonzero delta
    generated: list[tuple[str, str, dict]] = []
    for p, art in owner.items():
        c = result[int(art)]
        if manifest.PROSE_RE.match(p):
            o, n = old.read(p), new.read(p)
            counts = markdown_counts(o.decode("utf-8") if o is not None else None,
                                     n.decode("utf-8") if n is not None else "", smap=smap)
            c.prose += counts["prose"]
            c.heading += counts["heading"]
            c.table += counts["table"]
            c.suppressed += counts["suppressed"]
            c.new = c.new or o is None
            continue
        if any(u.get("typ") == p for u in doc[art].get("units", [])):
            note = (f"{p}: a layout unit changed. A person decides whether it changes "
                    f"what the Code says or only how it is laid out.")
            if p == "article-02.typ":
                note += " (The use-table legend lives in this file.)"
            c.needs_call.append(note)
            continue
        d = _declaration(doc, art, p)
        compare = d.get("compare") if d else None
        if compare == "json-keyed":
            delta = diff_maps(json_leaves(old.read(p), d), json_leaves(new.read(p), d))
            if delta.count():
                c.data += delta.count()
                c.data_detail[p] = delta
                real_source_change.add(p)
        elif compare == "binary-hash":
            c.needs_call.append(f"{p}: changed (binary). A person decides whether it changes the Code.")
        elif compare == "generated-from":
            generated.append((p, art, d))
        else:
            raise Refusal(f"{p}: unknown compare form {compare!r} in build/article-manifest.json")
    # A generated file is explained only by a source with a REAL (nonzero) data
    # delta: a re-indented or _meta-only source changes bytes and scores zero.
    for p, art, d in generated:
        src = d.get("from")
        if not isinstance(src, str):
            raise Refusal(f"{p}: declared generated-from in build/article-manifest.json "
                          f"but names no `from` source")
        if src not in real_source_change:
            result[int(art)].needs_call.append(
                f"{p}: changed although its source {src} did not change in data "
                f"(a re-indented or _meta-only source scores zero) -- an anomaly, "
                f"or a change to its other input (see the manifest note)")
    return result


# --- The CLI ----------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Which Articles changed in substance between two versions of the Code.")
    ap.add_argument("--old", required=True, help="the old version: a git ref")
    side = ap.add_mutually_exclusive_group()
    side.add_argument("--new-ref", help="the new version as a git ref")
    side.add_argument("--new-dir", help="the new version as a source directory (default: source/)")
    ap.add_argument("--section-map", help="a map from section_map.py derive; needs a directory new side")
    ap.add_argument("--article", type=int,
                    help="report one Article (every changed file is still classified)")
    ap.add_argument("--json", help="also write the determination as JSON to this path")
    a = ap.parse_args(argv)
    if a.json and Path(a.json).is_file():
        Path(a.json).unlink()        # a refusal must not leave an earlier run's file behind
    try:
        old = Side(ref=a.old)
        if a.new_ref:
            if a.section_map:
                raise Refusal("--section-map needs a directory new side (--new-dir): "
                              "a section map is checked against a tree")
            new = Side(ref=a.new_ref)
        else:
            new = Side(root=Path(a.new_dir) if a.new_dir else SOURCE)
        smap = None
        if a.section_map:
            import section_map
            problems = section_map.selfcheck(a.section_map, a.old, new.root)
            if problems:
                raise Refusal("the section map failed its self-check: " + "; ".join(problems))
            smap = section_map.load(a.section_map)
        result = determine(old, new, smap=smap)
        if a.article is not None and a.article not in result:
            raise Refusal(f"Article {a.article} is not in build/article-manifest.json")
    except Refusal as exc:
        print(f"czc_diff: refusing -- {exc}", file=sys.stderr)
        return 1

    shown = [c for n, c in sorted(result.items()) if a.article in (None, n)]
    print(f"Substantive-change determination: {old.label} -> {new.label}")
    print(f"  {'Article':>7} {'prose':>6} {'heading':>8} {'table':>6} {'data':>6} "
          f"{'suppressed':>11}  verdict")
    for c in shown:
        print(f"  {c.article:>7} {c.prose:>6} {c.heading:>8} {c.table:>6} {c.data:>6} "
              f"{c.suppressed:>11}  {c.verdict}{' (new)' if c.new else ''}")
    calls = [(c.article, note) for c in shown for note in c.needs_call]
    if calls:
        print("\nNeeds a person's call:")
        for art, note in calls:
            print(f"  Article {art}: {note}")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"old": old.label, "new": new.label,
             "articles": {str(c.article): c.as_json() for c in shown}},
            indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
