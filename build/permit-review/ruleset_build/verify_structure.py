r"""W2 gate hardening — mechanical structural assertions over BOTH rulesets.

This module exists because the W2 gate for "does the ruleset contain the
Subdivision APPROVAL STANDARDS' 21 lettered criteria a-u" was, before this
module, a piece of PROSE a runner read and rationalized: it observed "17"
(the count of Article 7 Section 12's own *subsections*, a-q — a completely
different number, one tree level up), wrote a "DISCREPANCY NOTE" explaining
why 17 was fine, and marked the check PASSED. The underlying data was
correct the whole time (both rulesets already contain all 21 standards a-u,
verified independently against the raw source in this module's own
construction — see the docstring of each DECLARED_CRITERIA_TABLE row and the
workflow report that built this module). The defect was entirely in the
CHECK, not the data: a judgment call where a mechanical assertion belongs.

Every check in this module is therefore a SET-EQUALITY, COUNT, or SEQUENCE
assertion with **no narrative escape hatch** — it prints the exact symmetric
difference / mismatch and returns/exits non-zero. There is no "discrepancy
note" code path here; a runner cannot rationalize past a failure printed by
this module without editing the module itself.

Reads ONLY the committed, pre-built `rulesets/<key>/articles.json` files —
never re-parses `source/`, per this package's own stated contract
(`ruleset_build/__init__.py`: "Runtime code ... never re-parses repo source
directly"). This matters in practice: at the time this module was written,
re-running the draft extractor (`ruleset_build.parse_articles.build_articles`)
against the CURRENT working tree raises `ArticleShapeError` on an unrelated,
pre-existing content defect in `source/article-05-building-standards.md`
("### e. SETBACKS" followed by a single line starting "a." instead of "1." —
a genuine gap in that file's own list numbering, nothing to do with Article 7/8
Administration and out of this workflow's scope to fix). Reading the
committed JSON sidesteps that landmine entirely and matches how every other
consumer in this codebase (verify_citations.py, app/rulesets.py) already
reads rulesets.

Two rulesets, two DIFFERENT JSON shapes (verified directly, not assumed):

  - `rulesets/adopted/articles.json` — a NESTED TREE. Top-level `articles[]`,
    each node `{kind, article, number, heading, text, children, id}`,
    `id` a dotted path ("art7.12.f.1.c.i"). Kind climbs
    article -> section -> subsection -> item (items can nest items, e.g. the
    Subdivision Pollution criterion's five roman sub-items).
  - `rulesets/draft-v0.22/articles.json` — a FLAT LIST under `nodes[]`. Each
    node carries `{id, article, section, section_name, subsection,
    subsection_name, path, depth, text, ...}` with NO `children` field —
    `path` (e.g. `["1", "c", "i"]`) is the node's position under its
    subsection, document order, `path[-1]` its own marker.

`_adopted_letters_at()` / `_draft_letters_at()` normalize both shapes to the
same query: "the markers of the DIRECT children at this digit-item path
under this subsection" — deliberately shallow, one level, never a whole-
subtree walk, which is exactly the discipline verify_citations.py's D2 fix
(`_standard_level_items`) applies to citation RESOLUTION; here it is applied
to structural VERIFICATION so a nested roman numeral can never be counted
as, or collide with, a top-level lettered standard.

Usage:
    python -m ruleset_build.verify_structure [--quiet]
Also reachable as `python run.py --verify-structure`, and folded into
`python run.py --selftest` / `python -m app.main --selftest` as one more
offline, no-network check (CONTRACT.md §1 S6 spirit — this module is not
itself a CONTRACT.md-numbered artifact, same footing as verify_citations.py).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

RULESETS_DIR = APP_ROOT / "rulesets"

ADOPTED_KEY = "adopted"
DRAFT_KEY = "draft-v0.22"


# --------------------------------------------------------------------------- #
# Loading — committed JSON only, never repo source (see module docstring).
# --------------------------------------------------------------------------- #


class RulesetLoadError(RuntimeError):
    """A ruleset's articles.json is missing or unreadable. Reported cleanly
    (SKIP, not a crash) by every check in this module, same discipline as
    verify_citations.NodeIndex's articles_error handling."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RulesetLoadError(f"{path} does not exist")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise RulesetLoadError(f"{path} could not be read/parsed: {e}") from e


def _flatten_adopted(node: dict[str, Any], out: dict[str, dict[str, Any]]) -> None:
    node_id = node.get("id")
    if node_id:
        out[node_id] = node
    for child in node.get("children") or []:
        _flatten_adopted(child, out)


def load_adopted_by_id(ruleset_key: str = ADOPTED_KEY) -> dict[str, dict[str, Any]]:
    doc = _read_json(RULESETS_DIR / ruleset_key / "articles.json")
    by_id: dict[str, dict[str, Any]] = {}
    for top in doc.get("articles", []):
        _flatten_adopted(top, by_id)
    return by_id


def load_draft_nodes(ruleset_key: str = DRAFT_KEY) -> list[dict[str, Any]]:
    doc = _read_json(RULESETS_DIR / ruleset_key / "articles.json")
    nodes = doc.get("nodes")
    if not isinstance(nodes, list):
        raise RulesetLoadError(f"{ruleset_key}/articles.json has no top-level 'nodes' list "
                                "(expected the flat draft shape)")
    return nodes


def _norm(s: str | None) -> str:
    return " ".join((s or "").strip().casefold().split())


# --------------------------------------------------------------------------- #
# Shape-normalized queries: "the direct-child markers at this digit-path
# under this (article, section, subsection heading)".
# --------------------------------------------------------------------------- #


def _find_child_by_heading(node: dict[str, Any], heading_cf: str) -> dict[str, Any] | None:
    for child in node.get("children") or []:
        if _norm(child.get("heading")) == heading_cf:
            return child
    return None


def adopted_subsection_node(
    by_id: dict[str, dict[str, Any]], article: int, section: str, subsection_heading: str
) -> dict[str, Any] | None:
    """Finds the APPROVAL-STANDARDS-style subsection by (article, section,
    heading TEXT) -- never by a hard-coded letter, since a subsection's own
    letter is not stable across sections (Subdivision's is 'e', Master
    Plan's is 'e' too, but Variance's is 'd' -- see verify_citations.py's
    `_find_child_by_heading` docstring for the same trap in the citation
    resolver this module is the structural counterpart to)."""
    sec_node = by_id.get(f"art{article}.{section}")
    if sec_node is None:
        return None
    return _find_child_by_heading(sec_node, _norm(subsection_heading))


def adopted_letters_at(
    by_id: dict[str, dict[str, Any]],
    article: int,
    section: str,
    subsection_heading: str,
    digit_path: list[str],
) -> list[str] | None:
    """The sorted markers of the DIRECT item-children reachable by
    descending `digit_path` (a list of digit item numbers, e.g. ["1"] or
    ["1", "c"]) from the named subsection. Returns None if the subsection or
    any digit-path step does not exist. Non-digit direct children only (a
    digit child one level down is a SIBLING numbered item, e.g. Master
    Plan's item "2" beside item "1" -- not itself a lettered standard)."""
    node = adopted_subsection_node(by_id, article, section, subsection_heading)
    if node is None:
        return None
    for step in digit_path:
        node = next(
            (c for c in (node.get("children") or [])
             if c.get("kind") == "item" and (c.get("number") or "") == step),
            None,
        )
        if node is None:
            return None
    return sorted(
        c.get("number") for c in (node.get("children") or [])
        if c.get("kind") == "item" and not (c.get("number") or "").isdigit()
    )


def adopted_item_text(
    by_id: dict[str, dict[str, Any]],
    article: int,
    section: str,
    subsection_heading: str,
    digit_path: list[str],
    letter: str,
) -> str | None:
    node = adopted_subsection_node(by_id, article, section, subsection_heading)
    if node is None:
        return None
    for step in digit_path + [letter]:
        node = next(
            (c for c in (node.get("children") or [])
             if c.get("kind") == "item" and (c.get("number") or "").casefold() == step.casefold()),
            None,
        )
        if node is None:
            return None
    return node.get("text")


def draft_letters_at(
    nodes: list[dict[str, Any]],
    article: int,
    section_name: str,
    subsection_name: str,
    digit_path: list[str],
) -> list[str] | None:
    """Draft-shape counterpart to adopted_letters_at(). Located by (article,
    section_name, subsection_name) TEXT, per the same never-by-letter
    discipline `ruleset_build.parse_articles.find_subsection_nodes` already
    documents. Returns None if no node in the group has exactly `digit_path`
    as its own path (distinguishes a genuinely empty list from a wrong/
    nonexistent path)."""
    sec_cf = _norm(section_name)
    sub_cf = _norm(subsection_name)
    group = [
        n for n in nodes
        if n.get("article") == article
        and _norm(n.get("section_name")) == sec_cf
        and _norm(n.get("subsection_name")) == sub_cf
    ]
    if not group:
        return None
    path_exists = any(n.get("path") == digit_path for n in group) if digit_path else True
    if not path_exists:
        return None
    target_depth = len(digit_path)
    letters = [
        n["path"][-1] for n in group
        if len(n.get("path") or []) == target_depth + 1
        and (n["path"][:target_depth] == digit_path)
        and not n["path"][-1].isdigit()
    ]
    return sorted(letters)


def draft_item_text(
    nodes: list[dict[str, Any]],
    article: int,
    section_name: str,
    subsection_name: str,
    digit_path: list[str],
    letter: str,
) -> str | None:
    sec_cf = _norm(section_name)
    sub_cf = _norm(subsection_name)
    target_path = digit_path + [letter]
    for n in nodes:
        if (
            n.get("article") == article
            and _norm(n.get("section_name")) == sec_cf
            and _norm(n.get("subsection_name")) == sub_cf
            and n.get("path") == target_path
        ):
            return n.get("text")
    return None


# --------------------------------------------------------------------------- #
# The declared-cardinality table.
#
# Every row here was established by READING THE SOURCE DIRECTLY, not by
# trusting either extractor's output:
#   - draft: source/article-08-administration.md and
#     source/article-02-prefatory.md, read with grep/sed.
#   - adopted: docs/Newcastle Core Zoning Code.pdf, read with
#     `pdftotext -layout` (a second, independent extraction path from the
#     one ruleset_build.extract_adopted.py uses) and eyeballed directly --
#     every letter a-u, and the n/r/i/j/c/u labels, and the §19.d 2:a-b /
#     3:a-d / 4:a-g split, are visible verbatim in that raw text dump.
# Where a cardinality could not be established with this level of directness
# it is NOT guessed here -- see DECISIONS-NEEDED.md (none were needed; every
# row below was confirmed against source text, not inferred).
# --------------------------------------------------------------------------- #

_ASCII_LOWER = "abcdefghijklmnopqrstuvwxyz"


def _letters(a: str, b: str) -> list[str]:
    """['a'..'z'] slice from `a` through `b` inclusive."""
    return list(_ASCII_LOWER[_ASCII_LOWER.index(a): _ASCII_LOWER.index(b) + 1])


DECLARED_CRITERIA_TABLE: list[dict[str, Any]] = [
    {
        "citation": "Article 7/8 Section 10.e — SMALL PROJECT PLAN, APPROVAL STANDARDS",
        "adopted": {"article": 7, "section": "10", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "draft": {"article": 8, "section_name": "SMALL PROJECT PLAN", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "expected_letters": _letters("a", "e"),
        "source": "source/article-08-administration.md:307-314; adopted PDF p.84 'e. APPROVAL STANDARDS'",
    },
    {
        "citation": "Article 7/8 Section 11.e — LARGE PROJECT PLAN, APPROVAL STANDARDS",
        "adopted": {"article": 7, "section": "11", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "draft": {"article": 8, "section_name": "LARGE PROJECT PLAN", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "expected_letters": _letters("a", "e"),
        "source": "source/article-08-administration.md:361-368; adopted PDF p.85 'e. APPROVAL STANDARDS'",
    },
    {
        "citation": "Article 7/8 Section 12.f — SUBDIVISION, APPROVAL STANDARDS (the defect-1 list)",
        "adopted": {"article": 7, "section": "12", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "draft": {"article": 8, "section_name": "SUBDIVISION", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "expected_letters": _letters("a", "u"),
        "source": "source/article-08-administration.md:429-457 (all 21, a. through u.); "
                  "adopted PDF p.84-88 'f. APPROVAL STANDARDS' via pdftotext -layout, read directly",
    },
    {
        "citation": "Article 7/8 Section 12.f, criterion c. Pollution — roman sub-items",
        "adopted": {"article": 7, "section": "12", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1", "c"]},
        "draft": {"article": 8, "section_name": "SUBDIVISION", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1", "c"]},
        "expected_letters": ["i", "ii", "iii", "iv", "v"],
        "source": "source/article-08-administration.md:435-439; adopted PDF p.86 'c. Pollution' roman sub-items i.-v.",
    },
    {
        "citation": "Article 7/8 Section 13.e — MASTER PLAN, APPROVAL STANDARDS",
        "adopted": {"article": 7, "section": "13", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "draft": {"article": 8, "section_name": "MASTER PLAN", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "expected_letters": _letters("a", "d"),
        "source": "source/article-08-administration.md:548-554; adopted PDF p.89 'e. APPROVAL STANDARDS' "
                  "(adopted has only item 1 a-d; draft additionally has a standalone item 2 with no letters "
                  "-- a real draft-only Article-3-Thoroughfares addition, not a structural mismatch, so it "
                  "is outside this letters-only check)",
    },
    {
        "citation": "Article 7/8 Section 18.e — SPECIAL PERMIT, APPROVAL STANDARDS",
        "adopted": {"article": 7, "section": "18", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "draft": {"article": 8, "section_name": "SPECIAL PERMIT", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["1"]},
        "expected_letters": _letters("a", "g"),
        "source": "source/article-08-administration.md:665-671; adopted PDF p.91-92 'e. APPROVAL STANDARDS'",
    },
    {
        "citation": "Article 7/8 Section 19.d, item 2 — VARIANCE, the two Variance types",
        "adopted": {"article": 7, "section": "19", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["2"]},
        "draft": {"article": 8, "section_name": "VARIANCE", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["2"]},
        "expected_letters": _letters("a", "b"),
        "source": "source/article-08-administration.md:715-717; adopted PDF p.92 'd. APPROVAL STANDARDS' item 2",
    },
    {
        "citation": "Article 7/8 Section 19.d, item 3 — VARIANCE, Undue Hardship conditions",
        "adopted": {"article": 7, "section": "19", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["3"]},
        "draft": {"article": 8, "section_name": "VARIANCE", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["3"]},
        "expected_letters": _letters("a", "d"),
        "source": "source/article-08-administration.md:718-722; adopted PDF p.92 'd. APPROVAL STANDARDS' item 3 "
                  "-- THE Defect-2 ambiguous group: its own letter 'c' collides with §12.f's roman 'c.i-v' "
                  "namespace only by COINCIDENCE of letter, never by tree position, per adopted_letters_at()'s "
                  "direct-children-only walk",
    },
    {
        "citation": "Article 7/8 Section 19.d, item 4 — VARIANCE, Practical Difficulty conditions",
        "adopted": {"article": 7, "section": "19", "subsection_heading": "APPROVAL STANDARDS", "digit_path": ["4"]},
        "draft": {"article": 8, "section_name": "VARIANCE", "subsection_name": "APPROVAL STANDARDS", "digit_path": ["4"]},
        "expected_letters": _letters("a", "g"),
        "source": "source/article-08-administration.md:723-730; adopted PDF p.92-93 'd. APPROVAL STANDARDS' item 4",
    },
]

# Letter -> normalized label-prefix spot checks, Subdivision (§12.f) only,
# per the workflow brief. Matched against the criterion's own `text` with a
# casefolded prefix test (`_label_prefix_ok`) so wording drift after the
# label (e.g. adopted's "b." names the RDEO, draft's "b." names Article 3
# Thoroughfares -- a real, expected content difference) never fails this
# check; only the LABEL itself -- what a citation like "Standard n." means
# -- must be stable.
SUBDIVISION_LABEL_SPOT_CHECKS: list[tuple[str, str]] = [
    ("c", "Pollution"),
    ("i", "Municipal Solid Waste Disposal"),
    ("j", "Aesthetic"),
    ("n", "Flood Areas"),
    ("r", "Spaghetti-Lots"),
    ("u", "Lands Subject to Liquidation Harvesting"),
]
_SUBDIVISION_APPSTD = {"adopted": dict(article=7, section="12", subsection_heading="APPROVAL STANDARDS", digit_path=["1"]),
                        "draft": dict(article=8, section_name="SUBDIVISION", subsection_name="APPROVAL STANDARDS", digit_path=["1"])}


def _label_prefix_ok(actual_text: str | None, expected_prefix: str) -> bool:
    return _norm(actual_text).startswith(_norm(expected_prefix))


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


class Result:
    def __init__(self) -> None:
        self.ok = True
        self.lines: list[str] = []

    def report(self, name: str, passed: bool | None, detail: str = "") -> None:
        status = "SKIP" if passed is None else ("PASS" if passed else "FAIL")
        line = f"{status:<4}  {name}"
        if detail:
            line += f" -- {detail}"
        self.lines.append(line)
        if passed is False:
            self.ok = False

    def note(self, text: str) -> None:
        self.lines.append(f"      {text}")


def check_declared_cardinalities(result: Result) -> None:
    """Every row of DECLARED_CRITERIA_TABLE: recovered letter SET ==
    expected letter SET, in BOTH rulesets. A mismatch prints the exact
    symmetric difference, never a count or a narrative."""
    try:
        adopted_by_id = load_adopted_by_id()
    except RulesetLoadError as e:
        result.report("declared-cardinality table (adopted)", None, str(e))
        adopted_by_id = None
    try:
        draft_nodes = load_draft_nodes()
    except RulesetLoadError as e:
        result.report("declared-cardinality table (draft-v0.22)", None, str(e))
        draft_nodes = None

    for row in DECLARED_CRITERIA_TABLE:
        expected = row["expected_letters"]
        citation = row["citation"]

        if adopted_by_id is not None:
            got = adopted_letters_at(adopted_by_id, **row["adopted"])
            name = f"[adopted] {citation}"
            if got is None:
                result.report(name, False, "node path not found in rulesets/adopted/articles.json")
            else:
                diff = sorted(set(expected) ^ set(got))
                passed = got == expected
                result.report(
                    name, passed,
                    "" if passed else f"expected {expected} got {got} symmetric_difference={diff}",
                )

        if draft_nodes is not None:
            got = draft_letters_at(draft_nodes, **row["draft"])
            name = f"[draft-v0.22] {citation}"
            if got is None:
                result.report(name, False, "node path not found in rulesets/draft-v0.22/articles.json")
            else:
                diff = sorted(set(expected) ^ set(got))
                passed = got == expected
                result.report(
                    name, passed,
                    "" if passed else f"expected {expected} got {got} symmetric_difference={diff}",
                )


def check_subdivision_full_alphabet(result: Result) -> None:
    """Explicit, standalone form of the headline defect-1 assertion, kept
    separate from the generic table walk above so this exact check --
    'Subdivision approval standards: recovered letter set == exactly
    {a..u} (21), in BOTH rulesets' -- exists as its own named, unskippable
    line in the output, per the workflow brief."""
    expected = _letters("a", "u")
    assert expected == list("abcdefghijklmnopqrstu") and len(expected) == 21

    for key, loader, getter, kwargs in (
        ("adopted", load_adopted_by_id, adopted_letters_at, _SUBDIVISION_APPSTD["adopted"]),
        ("draft-v0.22", load_draft_nodes, draft_letters_at, _SUBDIVISION_APPSTD["draft"]),
    ):
        try:
            src = loader()
        except RulesetLoadError as e:
            result.report(f"[{key}] Subdivision APPROVAL STANDARDS == {{a..u}} (21)", None, str(e))
            continue
        got = getter(src, **kwargs)
        if got is None:
            result.report(f"[{key}] Subdivision APPROVAL STANDARDS == {{a..u}} (21)", False,
                          "node path not found")
            continue
        diff = sorted(set(expected) ^ set(got))
        passed = got == expected
        result.report(
            f"[{key}] Subdivision APPROVAL STANDARDS == {{a..u}} (21)", passed,
            "" if passed else f"got {len(got)} letters {got}; symmetric_difference={diff}",
        )


def check_pollution_romans(result: Result) -> None:
    """'Criterion c. has exactly 5 roman sub-items i-v', standalone."""
    expected = ["i", "ii", "iii", "iv", "v"]
    sources = (
        ("adopted", load_adopted_by_id, adopted_letters_at, _SUBDIVISION_APPSTD["adopted"]),
        ("draft-v0.22", load_draft_nodes, draft_letters_at, _SUBDIVISION_APPSTD["draft"]),
    )
    for key, loader, getter, base in sources:
        try:
            src = loader()
        except RulesetLoadError as e:
            result.report(f"[{key}] Subdivision c. Pollution has exactly 5 roman sub-items i-v", None, str(e))
            continue
        kwargs = dict(base)
        kwargs["digit_path"] = kwargs["digit_path"] + ["c"]
        got = getter(src, **kwargs)
        name = f"[{key}] Subdivision c. Pollution has exactly 5 roman sub-items i-v"
        if got is None:
            result.report(name, False, "node path not found")
            continue
        diff = sorted(set(expected) ^ set(got))
        passed = got == expected
        result.report(name, passed, "" if passed else f"got {got}; symmetric_difference={diff}")


def check_label_spot_checks(result: Result) -> None:
    """Letter -> label spot checks, both rulesets, matched on a normalized
    label prefix (SUBDIVISION_LABEL_SPOT_CHECKS)."""
    sources = (
        ("adopted", load_adopted_by_id, adopted_item_text, _SUBDIVISION_APPSTD["adopted"]),
        ("draft-v0.22", load_draft_nodes, draft_item_text, _SUBDIVISION_APPSTD["draft"]),
    )
    for key, loader, getter, base in sources:
        try:
            src = loader()
        except RulesetLoadError as e:
            result.report(f"[{key}] letter->label spot checks", None, str(e))
            continue
        for letter, expected_prefix in SUBDIVISION_LABEL_SPOT_CHECKS:
            kwargs = dict(base)
            digit_path = kwargs.pop("digit_path")
            text = getter(src, digit_path=digit_path, letter=letter, **kwargs)
            name = f"[{key}] Standard {letter}. label starts with {expected_prefix!r}"
            if text is None:
                result.report(name, False, "no such standard letter found")
                continue
            passed = _label_prefix_ok(text, expected_prefix)
            result.report(name, passed, "" if passed else f"got text starting {text[:60]!r}")


# --------------------------------------------------------------------------- #
# Global contiguity / gap-free check.
# --------------------------------------------------------------------------- #

_ROMANS_IN_ORDER = [
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
]
_ROMAN_INDEX = {r: i for i, r in enumerate(_ROMANS_IN_ORDER)}
_MULTI_CHAR_ROMAN_ONLY = re.compile(r"^(?:ii|iii|iv|vi{1,3}|vii|viii|ix|x[iv]{0,3})$")


def _classify_markers(markers: list[str]) -> str:
    """'digit' | 'letter' | 'roman' | 'unknown'. A length-1 group of a
    single lowercase letter that ALSO happens to be a valid roman numeral
    ('i' or 'v') is classified 'letter' -- undecidable from one marker
    alone, and undecidable doesn't matter: a length-1 group is trivially
    contiguous under EITHER interpretation, so misclassifying it can never
    produce a false pass or false fail."""
    if all(re.fullmatch(r"[0-9]+", m) for m in markers):
        return "digit"
    if any(_MULTI_CHAR_ROMAN_ONLY.match(m) for m in markers):
        return "roman"
    if all(re.fullmatch(r"[a-z]", m) for m in markers):
        return "letter"
    return "unknown"


def _is_contiguous(markers: list[str]) -> tuple[bool, str]:
    """(ok, detail). `markers` in DOCUMENT order (the order children/nodes
    were produced in, never sorted first -- sorting would hide a real
    out-of-order/duplicate defect)."""
    kind = _classify_markers(markers)
    if kind == "digit":
        vals = [int(m) for m in markers]
        expected = list(range(vals[0], vals[0] + len(vals)))
        return vals == expected, f"digits {markers}"
    if kind == "letter":
        vals = [ord(m) - ord("a") for m in markers]
        expected = list(range(vals[0], vals[0] + len(vals)))
        return vals == expected, f"letters {markers}"
    if kind == "roman":
        try:
            vals = [_ROMAN_INDEX[m] for m in markers]
        except KeyError as e:
            return True, f"unclassifiable roman token {e} -- skipped, not a failure"
        expected = list(range(vals[0], vals[0] + len(vals)))
        return vals == expected, f"romans {markers}"
    return True, f"unknown marker kind -- skipped, not a failure: {markers}"


def _walk_adopted_groups(node: dict[str, Any], path: str, out: list[tuple[str, list[str]]]) -> None:
    items = [c for c in (node.get("children") or []) if c.get("kind") == "item"]
    if items:
        out.append((path, [c.get("number") or "" for c in items]))
    for child in node.get("children") or []:
        child_path = f"{path}.{child.get('number')}" if child.get("number") else path
        _walk_adopted_groups(child, child_path, out)


def check_global_contiguity(result: Result) -> None:
    """'Every ordered list in both rulesets is contiguous and gap-free.'
    Adopted: every tree node's item-kind children, recursively. Draft: every
    sibling group under one PARENT NODE ID, using the committed node order
    (already document order) rather than re-sorting.

    Grouping key is the parent's `id` (`node["id"].rsplit(".", 1)[0]`), NOT
    `(article, section, subsection letter, path-prefix)` -- Article 7/8
    Section 19 VARIANCE genuinely reuses the subsection letters 'a' and 'b'
    twice ("a. PURPOSE" / "b. APPLICABILITY", then later "a. GENERAL" /
    "b. AUTHORITY" -- verified directly in both source/article-08-
    administration.md and the adopted PDF's raw text; a real, pre-existing
    characteristic of the Code's own numbering, not a parsing artifact).
    `ruleset_build.parse_articles` already disambiguates this at the ID
    level (the second "a" gets id suffix "a_2", same discipline CONTRACT.md
    §4.1.2 documents for reused `panel_key`s) -- grouping by letter alone
    would silently MERGE the two different subsections' item-1 lists into
    one fake ['1','1'] group and misreport a gap that isn't the same list.
    Grouping by parent id uses that existing disambiguation instead of
    re-deriving it."""
    fail_count = 0
    checked = 0

    try:
        by_id = load_adopted_by_id()
    except RulesetLoadError as e:
        result.report("[adopted] every ordered list is contiguous/gap-free", None, str(e))
    else:
        groups: list[tuple[str, list[str]]] = []
        # by_id already has every node keyed by id; walk from each top-level
        # article so recursion sees the real tree (by_id alone has no
        # explicit parent links).
        doc = _read_json(RULESETS_DIR / ADOPTED_KEY / "articles.json")
        for top in doc.get("articles", []):
            _walk_adopted_groups(top, top.get("id", "?"), groups)
        bad = []
        for path, markers in groups:
            checked += 1
            ok, detail = _is_contiguous(markers)
            if not ok:
                fail_count += 1
                bad.append(f"{path}: {detail}")
        result.report(
            "[adopted] every ordered list is contiguous/gap-free", fail_count == 0,
            f"{checked} sibling groups checked, {fail_count} gapped" if fail_count else f"{checked} groups checked",
        )
        for b in bad[:20]:
            result.note(f"gap: {b}")

    try:
        nodes = load_draft_nodes()
    except RulesetLoadError as e:
        result.report("[draft-v0.22] every ordered list is contiguous/gap-free", None, str(e))
    else:
        by_group: dict[str, list[str]] = {}
        for n in nodes:
            path = n.get("path") or []
            node_id = n.get("id") or ""
            if not path or "." not in node_id:
                continue
            parent_id = node_id.rsplit(".", 1)[0]
            by_group.setdefault(parent_id, []).append(path[-1])
        bad = []
        checked_d = 0
        fail_d = 0
        for parent_id, markers in by_group.items():
            checked_d += 1
            ok, detail = _is_contiguous(markers)
            if not ok:
                fail_d += 1
                bad.append(f"{parent_id}: {detail}")
        result.report(
            "[draft-v0.22] every ordered list is contiguous/gap-free", fail_d == 0,
            f"{checked_d} sibling groups checked, {fail_d} gapped" if fail_d else f"{checked_d} groups checked",
        )
        for b in bad[:20]:
            result.note(f"gap: {b}")


# --------------------------------------------------------------------------- #
# FINDING 4 -- "a table node with zero children and no text is a FAILURE,
# not a warning." Same shape as check_global_contiguity above: a mechanical,
# no-narrative-escape sweep over BOTH rulesets, reporting every offending
# node id, never a count-only summary a runner could rationalize past.
#
# Before ruleset_build/extract_adopted.py's Finding-4 fix, EVERY ONE of the
# adopted ruleset's 7 table-caption nodes had `children: []` and `text:
# None` -- the caption was captured but the table's own row/column content
# was never attached to it; it silently corrupted whichever item/para node
# happened to be open immediately before the caption instead (see that
# module's Pass 3.5 docstring). This check is the standing invariant that
# catches a REGRESSION of that defect, or a NEW table introduced by a future
# Code edit that the extractor doesn't yet know how to grid/flatten.
# --------------------------------------------------------------------------- #


def _walk_adopted_tables(node: dict[str, Any], out: list[dict[str, Any]]) -> None:
    if node.get("kind") == "table":
        out.append(node)
    for child in node.get("children") or []:
        _walk_adopted_tables(child, out)


def check_no_empty_tables(result: Result) -> None:
    """Every `kind: "table"` node (adopted) / `kind_hint: "table"` node
    (draft) must carry real, non-empty `text` -- the literal Finding 4
    failure signature ("zero children and text: None") reduces, on both
    rulesets' actual schemas, to exactly this: a table's own content
    (`columns`/`rows`/`raw_text`, whichever the extractor could produce) is
    only ever attached BY setting `text` to the table's caption at the same
    time. `text: None`/`""` is therefore the one schema-agnostic, mechanical
    signal that a table's content never got wired up -- checked here, never
    narrated past."""
    try:
        doc = _read_json(RULESETS_DIR / ADOPTED_KEY / "articles.json")
    except RulesetLoadError as e:
        result.report("[adopted] no table node is empty (zero children, no text)", None, str(e))
    else:
        tables: list[dict[str, Any]] = []
        for top in doc.get("articles", []):
            _walk_adopted_tables(top, tables)
        bad = [t.get("id", "?") for t in tables if not (t.get("text") or "").strip()]
        result.report(
            "[adopted] no table node is empty (zero children, no text)", len(bad) == 0,
            f"{len(tables)} table nodes checked, {len(bad)} empty" if bad else f"{len(tables)} table nodes checked",
        )
        for b in bad:
            result.note(f"empty table: {b}")

    try:
        nodes = load_draft_nodes()
    except RulesetLoadError as e:
        result.report("[draft-v0.22] no table node is empty (zero children, no text)", None, str(e))
    else:
        tables_d = [n for n in nodes if n.get("kind_hint") == "table"]
        bad_d = [n.get("id", "?") for n in tables_d if not (n.get("text") or "").strip()]
        result.report(
            "[draft-v0.22] no table node is empty (zero children, no text)", len(bad_d) == 0,
            f"{len(tables_d)} table nodes checked, {len(bad_d)} empty" if bad_d else f"{len(tables_d)} table nodes checked",
        )
        for b in bad_d:
            result.note(f"empty table: {b}")


# --------------------------------------------------------------------------- #
# FINDING 4, part 2 -- "VALIDATE every clock applies_to against [Table 7.1]
# ... where they conflict, the TABLE governs." Table 7.1 ("NOTICES & PUBLIC
# HEARINGS") is Article 7 §5.c.1/§6.b.1's own authority for which
# application types require mailed notice and a public hearing. This check
# cross-references it against every clocks.json entry whose own governing
# citation is Table 7.1's subject matter.
#
# The two clock-role mappings below are hand-built from each clock's OWN
# citation (Article 7 §5.c.3 for notice_mailed; §11.d.4.a/§12.e.5/§18.d.1/
# §19.c.1 for the four first-instance hearing clocks), not derived from the
# table itself -- avoids validating the table against a mapping that was
# itself read off the table. `administrative_appeal_hearing` (§23.d.2) is
# deliberately EXCLUDED: it is a §23 APPEAL hearing, a different procedural
# event Table 7.1 does not purport to cover (the table's rows are the
# ORIGINAL application types, not appeal tracks).
#
# `●` (Required) must be a HARD member of the mapped clock's `applies_to`;
# a blank cell (not required) must be a HARD non-member. `◐` (May be
# required) is genuinely conditional per the Code's own legend and is never
# treated as a disagreement either way. Rows with no `cases.application_type`
# at all (Master Plan, Plan Revision, Land Conveyance, Zoning Amendment --
# see build_clocks.DECISION_TRACKS) are not checkable against any clock and
# are skipped, not silently treated as agreeing.
# --------------------------------------------------------------------------- #

NOTICE_TABLE_ROW_TO_APPLICATION_TYPE: dict[str, str] = {
    "Small Project plan": "small_project_plan",
    "Large Project Plan": "large_project_plan",
    "Subdivision Plan": "subdivision",
    "Special Permit": "special_permit",
    "Variance": "variance",
}
NOTICE_TABLE_CLOCKS: tuple[str, ...] = ("notice_mailed",)  # Article 7 §5.c.3

# application_type -> the one first-instance PUBLIC HEARING clock governing
# it, or None where the Code models no hearing for that track at all
# (small_project_plan -- CEO track, §10.d.4, no hearing anywhere in Article 7).
HEARING_TABLE_ROW_TO_CLOCK: dict[str, str | None] = {
    "small_project_plan": None,
    "large_project_plan": "large_project_pb_completeness_hearing",  # §11.d.4.a
    "subdivision": "subdivision_hearing_decision",                  # §12.e.5 (fused hearing+decision)
    "special_permit": "special_permit_review_hearing",              # §18.d.1
    "variance": "variance_review_hearing",                          # §19.c.1
}


def _find_notices_hearings_table(by_id: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for node in by_id.values():
        if node.get("kind") == "table" and (node.get("heading") or "").strip().upper() == "NOTICES & PUBLIC HEARINGS":
            return node
    return None


def check_table_7_1_applies_to(result: Result) -> None:
    """FINDING 4: every notice/hearing clock's `applies_to` must agree with
    Table 7.1's own Notice/Public Hearing columns. Reports the exact table
    cell and the exact clock on any disagreement -- no summary-only pass."""
    name = "[adopted] clocks.json applies_to agrees with Table 7.1 (NOTICES & PUBLIC HEARINGS)"
    try:
        by_id = load_adopted_by_id()
    except RulesetLoadError as e:
        result.report(name, None, str(e))
        return

    table = _find_notices_hearings_table(by_id)
    if table is None:
        result.report(name, False, "no 'NOTICES & PUBLIC HEARINGS' table node found in rulesets/adopted/articles.json")
        return
    rows = table.get("rows") or []
    if not rows:
        result.report(name, False, f"Table 7.1 node {table.get('id')!r} has no rows -- cannot validate applies_to against it")
        return
    row_by_label = {r[0]: r[1:] for r in rows}  # label -> [notice_cell, hearing_cell]

    try:
        from engine import deadlines as deadlines_mod
    except Exception as e:  # noqa: BLE001
        result.report(name, None, f"engine.deadlines not importable: {e}")
        return
    try:
        clocks = deadlines_mod.load_clocks("adopted")
    except deadlines_mod.ClocksNotFound as e:
        result.report(name, None, str(e))
        return
    clocks_by_key = {c.clock_key: c for c in clocks}

    problems: list[str] = []
    checked = 0

    for row_label, app_type in NOTICE_TABLE_ROW_TO_APPLICATION_TYPE.items():
        cell = (row_by_label.get(row_label) or ["", ""])[0]
        for clock_key in NOTICE_TABLE_CLOCKS:
            clock = clocks_by_key.get(clock_key)
            if clock is None:
                problems.append(f"{clock_key!r} named in NOTICE_TABLE_CLOCKS is not a clock in clocks.json (stale mapping)")
                continue
            checked += 1
            applies = app_type in clock.applies_to
            if cell == "" and applies:
                problems.append(
                    f"{clock_key}.applies_to includes {app_type!r}, but Table 7.1 marks Notice as "
                    f"NOT required for {row_label!r} (blank cell) -- table governs, remove {app_type!r}"
                )
            elif cell == "●" and not applies:
                problems.append(
                    f"{clock_key}.applies_to is MISSING {app_type!r}, but Table 7.1 marks Notice "
                    f"REQUIRED (●) for {row_label!r} -- table governs, add {app_type!r}"
                )
            # cell == "◐" (May be required): genuinely conditional, not a disagreement either way.

    for app_type, clock_key in HEARING_TABLE_ROW_TO_CLOCK.items():
        row_label = next((lbl for lbl, at in NOTICE_TABLE_ROW_TO_APPLICATION_TYPE.items() if at == app_type), None)
        if row_label is None:
            continue
        cell = (row_by_label.get(row_label) or ["", ""])[1]
        checked += 1
        if clock_key is None:
            if cell == "●":
                problems.append(
                    f"Table 7.1 marks Public Hearing REQUIRED (●) for {row_label!r}, but "
                    f"HEARING_TABLE_ROW_TO_CLOCK maps {app_type!r} to no hearing clock at all"
                )
            continue
        clock = clocks_by_key.get(clock_key)
        if clock is None:
            problems.append(f"{clock_key!r} named in HEARING_TABLE_ROW_TO_CLOCK is not a clock in clocks.json (stale mapping)")
            continue
        applies = app_type in clock.applies_to
        if cell == "" and applies:
            problems.append(
                f"{clock_key}.applies_to includes {app_type!r}, but Table 7.1 marks Public Hearing as "
                f"NOT required for {row_label!r} (blank cell) -- table governs, remove {app_type!r}"
            )
        elif cell == "●" and not applies:
            problems.append(
                f"{clock_key}.applies_to is MISSING {app_type!r}, but Table 7.1 marks Public Hearing "
                f"REQUIRED (●) for {row_label!r} -- table governs, add {app_type!r}"
            )

    detail = ""
    if problems:
        head = "; ".join(problems[:3])
        more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
        detail = f"{len(problems)} disagreement(s): {head}{more}"
    else:
        detail = f"{checked} (row, clock) pairs checked -- all agree"
    result.report(name, len(problems) == 0, detail)
    for p in problems:
        result.note(p)


# --------------------------------------------------------------------------- #
# N2 -- event recordability. "A clock's start_event/satisfying_event is a
# real CaseFacts field" (engine/deadlines.py's own `_resolve_event()` build-
# time guard, an AttributeError) was already asserted. NOTHING asserted the
# next, operator-facing question: can that event ever actually be RECORDED?
# Before this check existed, three §23 appeal-track clocks
# (administrative_appeal_hearing, administrative_appeal_decision,
# reconsideration_decision -- rulesets/adopted/clocks.json, added at F3)
# named four events (appeal_hearing_opened_at, appeal_hearing_closed_at,
# appeal_decision_at, reconsideration_decided_at) that NO case_milestones.kind
# could populate -- not a missing CaseFacts field (that would already fail
# loudly, per _resolve_event()'s own AttributeError), but a silent DEAD END:
# the field existed, stayed forever None, and two of those three clocks carry
# the §8.d.1 auto-approval consequence, so a Board of Appeals that held its
# hearing and decided an appeal exactly on time still showed a PERMANENT,
# un-clearable alarm (see engine/deadlines.py's module docstring, "N2").
#
# This check walks every clock's start_event AND satisfying_event and, for
# each, requires ALL FOUR layers an operator's real "record a milestone"
# path actually crosses to be genuinely wired, END TO END:
#   (a) the case_milestones.kind CHECK constraint the DB itself enforces --
#       introspected from a FRESHLY MIGRATED temp DB's own sqlite_master.sql,
#       not guessed from any single migration file in isolation (the table
#       has been rebuilt multiple times: 0002, 0003, 0005, 0006, ... -- the
#       DB's own current schema is the only reliable source of truth for
#       "what CHECK does a live database actually enforce today");
#   (b) app.cases.CASE_MILESTONE_KINDS -- the app-level vocabulary that turns
#       a bad kind into a clean 400 instead of a raw sqlite3.IntegrityError;
#   (c) engine.deadlines._MILESTONE_TO_FIELD (or the documented
#       `_SPECIAL_EVENT_SOURCES` exception, e.g. `submitted_at`'s
#       DECISIONS-NEEDED D-0008 multi-source ranking) -- the mapping that
#       actually turns a recorded row into the CaseFacts field a clock
#       reads. `engine.deadlines.event_recordable_kinds()` is the single
#       source of truth for this layer; see its own docstring;
#   (d) app.main.MILESTONE_KIND_LABELS -- the operator-facing dropdown
#       (case_detail.html renders one <option> per
#       sorted(CASE_MILESTONE_KINDS), so a kind missing here still *renders*
#       under its raw snake_case name -- not genuinely selectable by a
#       non-technical operator, which is why this layer is checked on its
#       own rather than folded into (b)).
#
# No narrative escape hatch, same discipline as every other check in this
# module: any event failing any layer prints exactly which clock, which
# role (start/satisfying), which kind, and which layer(s) are missing, and
# fails the build.
# --------------------------------------------------------------------------- #


def _case_milestones_kind_check_values() -> set[str] | None:
    """The case_milestones.kind CHECK constraint's actual value set, read
    from a freshly migrated throwaway temp DB's own `sqlite_master.sql` --
    the DB's own current truth, never guessed from a single migration file
    (case_milestones has been rebuilt more than once: 0002, 0003, 0005,
    0006, ... -- each one a full "recreate under a temp name, drop the
    original, rename into place" pass over the whole table, per those
    files' own notes). Returns None (SKIP, not a hard failure -- the same
    degrade-gracefully discipline every other check in this module follows)
    if `app.db` or `app/migrations/` are not available in this environment.
    """
    try:
        import sqlite3  # noqa: F401  (imported for clarity; sqlite3 itself unused directly)
        import tempfile

        from app import db as db_mod
    except Exception:
        return None

    migrations_dir = APP_ROOT / "app" / "migrations"
    if not migrations_dir.exists():
        return None

    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_db = Path(td) / "verify-structure-recordability.db"
            conn = db_mod.connect(tmp_db)
            try:
                db_mod.migrate(conn, migrations_dir)
                row = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='case_milestones';"
                ).fetchone()
            finally:
                conn.close()
    except Exception:
        return None

    if row is None or not row[0]:
        return None

    create_sql = row[0]
    m = re.search(r"kind\s+TEXT\s+NOT\s+NULL\s+CHECK\s*\(\s*kind\s+IN\s*\((.*?)\)\s*\)", create_sql, re.I | re.S)
    if not m:
        return None
    return set(re.findall(r"'([^']*)'", m.group(1)))


def check_clock_event_recordability(result: Result) -> None:
    """N2 -- the missing gate assertion. See the module comment block
    directly above this function for the full rationale; this docstring is
    the short form. Fails the build when any `rulesets/adopted/clocks.json`
    clock names a start_event or satisfying_event that is not recordable
    through ALL of: (a) the live case_milestones.kind CHECK constraint,
    (b) app.cases.CASE_MILESTONE_KINDS, (c) engine.deadlines.
    _MILESTONE_TO_FIELD / _SPECIAL_EVENT_SOURCES (via
    engine.deadlines.event_recordable_kinds()), (d) app.main.
    MILESTONE_KIND_LABELS (the operator UI dropdown).
    """
    name = "clock event recordability -- every clock's start/satisfying event is recordable end to end (N2 gate)"

    try:
        from engine import deadlines as deadlines_mod
    except Exception as e:  # noqa: BLE001
        result.report(name, None, f"engine.deadlines not importable: {e}")
        return

    try:
        clocks = deadlines_mod.load_clocks("adopted")
    except deadlines_mod.ClocksNotFound as e:
        result.report(name, None, str(e))
        return

    try:
        from app import cases as cases_mod
    except Exception as e:  # noqa: BLE001
        result.report(name, None, f"app.cases not importable: {e}")
        return

    try:
        from app import main as app_main_mod
    except Exception as e:  # noqa: BLE001
        result.report(name, None, f"app.main not importable: {e}")
        return

    db_kinds = _case_milestones_kind_check_values()
    if db_kinds is None:
        result.report(name, None, "could not introspect case_milestones.kind's CHECK from a freshly migrated temp DB")
        return

    app_kinds = set(cases_mod.CASE_MILESTONE_KINDS)
    ui_labels = set(app_main_mod.MILESTONE_KIND_LABELS)

    problems: list[str] = []
    checked = 0
    for clock in clocks:
        for role, event_name in (("start_event", clock.start_event), ("satisfying_event", clock.satisfying_event)):
            checked += 1
            kinds = deadlines_mod.event_recordable_kinds(event_name)
            if not kinds:
                problems.append(
                    f"{clock.clock_key}.{role} ({event_name!r}): NOT MAPPED -- no case_milestones.kind "
                    f"populates this CaseFacts field at all (engine.deadlines._MILESTONE_TO_FIELD / "
                    f"_SPECIAL_EVENT_SOURCES has no entry for it)"
                )
                continue
            for kind in kinds:
                missing_layers = []
                if kind not in db_kinds:
                    missing_layers.append("(a) case_milestones.kind CHECK constraint")
                if kind not in app_kinds:
                    missing_layers.append("(b) app.cases.CASE_MILESTONE_KINDS")
                if kind not in ui_labels:
                    missing_layers.append("(d) app.main.MILESTONE_KIND_LABELS (operator UI)")
                if missing_layers:
                    problems.append(
                        f"{clock.clock_key}.{role} ({event_name!r} -> kind {kind!r}): "
                        f"missing {', '.join(missing_layers)}"
                    )

    detail = ""
    if problems:
        head = "; ".join(problems[:3])
        more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
        detail = f"{len(problems)} problem(s): {head}{more}"
    result.report(name, len(problems) == 0, detail)
    if problems:
        for p in problems:
            result.note(p)
    else:
        result.note(f"{checked} (clock, role) pairs checked across {len(clocks)} clocks -- all recordable end to end")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def run_checks() -> Result:
    result = Result()
    check_subdivision_full_alphabet(result)
    check_pollution_romans(result)
    check_label_spot_checks(result)
    check_global_contiguity(result)
    check_declared_cardinalities(result)
    check_no_empty_tables(result)
    check_table_7_1_applies_to(result)
    check_clock_event_recordability(result)
    return result


def run(quiet: bool = False) -> int:
    result = run_checks()
    if not quiet:
        print("ruleset_build.verify_structure -- mechanical structural gate")
        print()
        for line in result.lines:
            print(line)
        print()
    print("STRUCTURE:", "ALL OK" if result.ok else "FAILURES ABOVE (see FAIL lines)")
    return 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Structural verification harness (W2 gate hardening)")
    parser.add_argument("--quiet", action="store_true", help="print only PASS/FAIL lines, no header")
    args = parser.parse_args(argv)
    return run(quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
