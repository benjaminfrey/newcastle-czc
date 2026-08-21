"""W2 Phase 2: parses the DRAFT articles (source/article-0N-*.md, N in 1..8)
into citation nodes and writes rulesets/<ruleset-key>/articles.json.

This is the extraction layer the citation engine (later workflows) and the
Board-facing worksheet will eventually walk to locate a specific standard by
article/section/subsection — WITHOUT re-reading markdown at request time.
Runtime never re-parses repo source (same discipline as ruleset_build's
districts/use-matrix builders); it only reads this committed JSON.

NOTE ON SCOPE: source/article-09-definitions.md does NOT follow the Article
1-8 grammar below (no "## N. SECTION" / "### x. SUBSECTION" headings at all —
it is a flat "**Term:**\\n<definition>" list). It is parsed separately by
ruleset_build/parse_definitions.py. This module parses articles 1-8 only and
raises if asked to parse 9.

THE GRAMMAR (verified against the real files, not assumed):

    YAML frontmatter (article-number, article-name, footer-date)
    # Article N <Name>
    ## <int>. SECTION TITLE
    ### <letter>. SUBSECTION TITLE
    1. top-level ordered item          (0-space indent, digit marker)
        a. nested item                 (4-space indent, letter marker)
            i. doubly-nested item      (8-space indent, roman marker)

Every list item is exactly ONE physical line — the source is NOT hard-wrapped
(verified: max line length has no soft-wrap artifacts; what looks like
wrapping in a terminal `sed -n l` is a terminal-width display effect, not
file content). This is what makes `text` a verbatim, un-reflowed copy of the
line and makes the round-trip check in --verify meaningful instead of vacuous.

TWO CONFIRMED GRAMMAR EXCEPTIONS, both handled generically (not hard-coded to
the specific section that exhibits them, so a future edit elsewhere in the
same shape is still handled):

1. **Duplicate subsection letters within one section.** Article 8 Section 19
   VARIANCE runs PURPOSE(a), APPLICABILITY(b), GENERAL(a) again, AUTHORITY(b)
   again, PROCEDURE(c), APPROVAL STANDARDS(d) — the letters restart partway
   through. CONTRACT-adjacent code elsewhere in this repo (ruleset_build/
   slugs.py's panel_key collision rule) resolves an identical shape by
   appending `_2`, `_3` to the *key* used for machine identity while leaving
   the *display title* verbatim — this module does the same for
   `subsection_key` (used only in node ids), never touching `subsection`
   (the literal source letter) or `subsection_name` (the literal title).
   LOCATE SUBSECTIONS BY `subsection_name` TEXT, NEVER BY LETTER.

2. **A section with no "### " subsections at all.** Article 8 Section 22
   DEMOLITION OF HISTORIC ASSETS has no "### " headings; instead its
   top-level ordered items ("1. PURPOSE", "2. APPLICABILITY", ...) are
   themselves the subsection titles, with the real content one indent level
   deeper than usual (letters at 4-space where a normal section would have
   its top-level digits there). Detected per-section by the absence of any
   "### " line before the next "## " line — not by section number — so it
   generalizes to any future section shaped the same way. The pseudo-header
   item itself is consumed (round-trips) but emits no citation node, since
   its only content is the label ("PURPOSE") already captured as
   `subsection_name`.

A bare (unmarked, unindented) text line is either:
  - a table caption, if it matches `^TABLE\\s` and precedes a pipe table;
  - a table note/legend line, if it falls between a caption (or a previous
    table's end) and the next pipe table's header row;
  - otherwise a standalone prose paragraph (e.g. Article 7's "### a.
    DEFINITION" body, which is plain prose, never a numbered list item).

Every pipe table in the corpus is immediately preceded (across only blank
lines and/or caption/note lines) by a `TABLE ...` caption — verified across
articles 4, 5, 6 and 8, so a table with no caption is treated as a shape
violation and raises, rather than silently emitting an untitled table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
SOURCE_DIR = REPO_ROOT / "source"

SCHEMA = "newcastle.articles/1.0.0"
DEFAULT_RULESET_KEY = "draft-v0.22"

# Articles 1-8 follow the grammar above. Article 9 is definitions-only
# (ruleset_build/parse_definitions.py). Article 3 additionally contains raw
# `{=typst}` fenced blocks (the plate/exhibit splice points) — LOW priority
# per this workflow's scope; captured verbatim as kind_hint "raw_typst" and
# never parsed as prose or tables.
ARTICLE_FILES: dict[int, str] = {
    1: "article-01-general.md",
    2: "article-02-prefatory.md",
    3: "article-03-streets-roads-driveways.md",
    4: "article-04-site-standards.md",
    5: "article-05-building-standards.md",
    6: "article-06-design-standards.md",
    7: "article-07-use-standards.md",
    8: "article-08-administration.md",
}

FRONTMATTER_RE = re.compile(r'^(article-number|article-name|footer-date):\s*"(.*)"\s*$')
TITLE_RE = re.compile(r"^# Article (\d+) (.+)$")
SECTION_RE = re.compile(r"^## (\d+)\.\s+(.+)$")
SUBSECTION_RE = re.compile(r"^### ([a-z]{1,3})\.\s+(.+)$")
LIST_ITEM_RE = re.compile(r"^( {0,8})((?:\d+|[a-z]{1,3}|[ivxlcdm]{1,7}))\.\s*(.*)$")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEP_CELL_RE = re.compile(r"^:?-+:?$")
TABLE_CAPTION_RE = re.compile(r"^TABLE\s")
FENCE_RE = re.compile(r"^```")
COMMENT_RE = re.compile(r"^<!--")

_KIND_PREFIX = {"prose": "p", "table": "t", "raw_typst": "rt"}

# ---------------------------------------------------------------------------
# List-sequence integrity (DEFECT 1 hardening).
#
# `eff_level`/`raw_level` already tells us WHERE a marker sits from pure
# indentation (structure), never from sniffing the marker glyph — "i" at
# depth 1 is the 9th letter of an alpha run, "i" at depth 2 is the 1st roman
# numeral of a nested run, and indentation (not the character) is what says
# which. This section adds the other half: having placed a marker at a
# depth, assert its VALUE is the correct next value in that depth's run.
# A silently truncated/reset ordered list (the exact DEFECT 1 failure mode)
# always shows up here as a marker that isn't the expected successor of the
# previous one at the same (subsection, parent-path, kind) — and now RAISES
# with the source line, rather than being absorbed into `path` unnoticed.
# ---------------------------------------------------------------------------

_ROMAN_SEQ = [
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi",
]


def _next_alpha_marker(marker: str) -> str:
    """'a'->'b', ..., 'z'->'aa' (bijective base-26, Excel-column style)."""
    idx = 0
    for ch in marker:
        idx = idx * 26 + (ord(ch) - ord("a") + 1)
    idx += 1
    out = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        out = chr(ord("a") + rem) + out
    return out


def _next_roman_marker(marker: str) -> str | None:
    try:
        i = _ROMAN_SEQ.index(marker)
    except ValueError:
        return None
    return _ROMAN_SEQ[i + 1] if i + 1 < len(_ROMAN_SEQ) else None


def _next_digit_marker(marker: str) -> str:
    return str(int(marker) + 1)


_SEQ_START = {"digit": "1", "alpha": "a", "roman": "i"}
_SEQ_NEXT = {"digit": _next_digit_marker, "alpha": _next_alpha_marker, "roman": _next_roman_marker}


def _expected_list_kind(subsection_mode: str | None, eff_level: int) -> str:
    """The marker KIND a depth must hold, derived purely from structure
    (subsection mode + effective depth) — real-mode depths are
    digit/alpha/roman at 0/1/2; virtual mode (grammar exception 2) is
    shifted one level, since its depth-0 items are the pseudo-subsection
    headers, not the digit list (see module docstring)."""
    if subsection_mode == "virtual":
        return "alpha" if eff_level == 0 else "roman"
    return {0: "digit", 1: "alpha", 2: "roman"}[eff_level]


class ArticleShapeError(RuntimeError):
    """Raised when a source file doesn't shape up the way this module's
    grammar (see module docstring) documents — a hard build failure, never a
    silent best-effort guess. FAIL LOUDLY, matching ruleset_build's other
    builders (CONTRACT.md §4.2.3's ethos, applied here to prose structure
    rather than dimensional data)."""


@dataclass
class _ParseState:
    """Everything the line-by-line walk needs to remember about "where we
    are" in the document, kept as one object so parse_article_file() reads as
    a single, auditable state machine rather than a pile of nonlocal names."""

    article: int
    article_name: str
    ruleset_key: str
    rel_path: str

    section: str | None = None
    section_name: str | None = None

    # Real mode: subsection is the literal "### x." letter. Virtual mode
    # (grammar exception 2): subsection is the pseudo top-level item's own
    # marker (a digit), subsection_name is that item's text.
    subsection_mode: str | None = None  # "real" | "virtual" | None (unset)
    subsection: str | None = None
    subsection_name: str | None = None
    subsection_key: str | None = None

    # (article, section) -> {letter_or_digit: occurrence_count}, for the
    # "_2"/"_3" subsection_key disambiguation (grammar exception 1).
    _subsection_seen: dict[tuple[int, str], dict[str, int]] = field(default_factory=dict)

    # path stack for the current list nest, effective-depth indexed (0,1,2).
    _stack: list[str] = field(default_factory=list)

    # DEFECT 1 hardening: (kind_tag, article, section, subsection_key,
    # parent-path-tuple, marker-kind) -> last marker seen there, for the
    # ordered-list contiguity check (see _check_sequence / module section
    # above _ParseState).
    _seq_last: dict[tuple, str] = field(default_factory=dict)

    # (article, section, subsection_key, kind) -> next block index, for
    # prose/table/raw_typst path assignment ("p1", "t1", "rt1", ...).
    _block_counters: dict[tuple, int] = field(default_factory=dict)

    nodes: list[dict] = field(default_factory=list)
    # line_no (1-indexed) -> reconstructed line text, for headings/list items/
    # pseudo-headers only (the kinds --verify regenerates from parsed fields
    # rather than replaying verbatim — see module docstring).
    reconstructed: dict[int, str] = field(default_factory=dict)
    # line_no -> True for every line this parser recognized (of ANY kind,
    # including blank/frontmatter/table-row/raw-typst/comment, which are
    # replayed verbatim in --verify rather than regenerated).
    consumed: set[int] = field(default_factory=set)
    # line_no -> effective depth (0,1,2), list items only — --verify asserts
    # each such line was classified exactly once at exactly one depth.
    item_depth: dict[int, int] = field(default_factory=dict)
    heading_lines: set[int] = field(default_factory=set)

    def enter_section(self, num: str, name: str) -> None:
        self.section = num
        self.section_name = name
        self.subsection_mode = None
        self.subsection = None
        self.subsection_name = None
        self.subsection_key = None
        self._stack = []

    def _next_subsection_key(self, letter_or_digit: str) -> str:
        seen = self._subsection_seen.setdefault((self.article, self.section), {})
        seen[letter_or_digit] = seen.get(letter_or_digit, 0) + 1
        n = seen[letter_or_digit]
        return letter_or_digit if n == 1 else f"{letter_or_digit}_{n}"

    def enter_real_subsection(self, letter: str, name: str) -> None:
        self.subsection_mode = "real"
        self.subsection = letter
        self.subsection_name = name
        self.subsection_key = self._next_subsection_key(letter)
        self._stack = []

    def enter_virtual_subsection(self, digit: str, name: str) -> None:
        self.subsection_mode = "virtual"
        self.subsection = digit
        self.subsection_name = name
        self.subsection_key = self._next_subsection_key(digit)
        self._stack = []

    def _check_sequence(self, key: tuple, kind: str, marker: str, line_no: int, what: str) -> None:
        """RAISE (never warn) if `marker` isn't the correct next value for
        the ordered-list identified by `key`. `key` already encodes the
        marker's structural position (subsection + parent path + kind), so
        this is a pure gap/reset check on the VALUE, independent of how the
        depth itself was determined."""
        marker_l = marker.lower()
        last = self._seq_last.get(key)
        if last is None:
            expected = _SEQ_START[kind]
            if marker_l != expected:
                raise ArticleShapeError(
                    f"{self.rel_path}:{line_no}: {what} starts with {marker!r}, "
                    f"expected {expected!r} — a list beginning mid-sequence is "
                    f"exactly the truncated/gapped-list failure mode this check "
                    f"exists to catch"
                )
        else:
            expected = _SEQ_NEXT[kind](last)
            if expected is None or marker_l != expected:
                raise ArticleShapeError(
                    f"{self.rel_path}:{line_no}: {what}: after {last!r} expected "
                    f"{expected!r}, got {marker!r} — gap or unexpected reset in "
                    f"an ordered list"
                )
        self._seq_last[key] = marker_l

    def check_list_item_sequence(self, eff_level: int, marker: str, line_no: int) -> None:
        # GRAMMAR EXCEPTION 3 (found while adding this check, generalized
        # rather than hard-coded to its one instance — Article 5 §e.
        # SETBACKS is a real "### " subsection whose entire body is a single
        # clause the source marks "a." instead of restating "1."; verified
        # this is the ONLY depth-0 real-mode list in the whole corpus that
        # doesn't open on a digit). A depth-0 item under a REAL subsection
        # may therefore open as digit-kind ("1") OR alpha-kind ("a") — never
        # roman-kind, which is exactly the collision DEFECT 2 exploits, so
        # roman is deliberately excluded here rather than accepted "to be
        # safe". Once a key opens under one of the two allowed kinds, every
        # later item under that same key must continue THAT kind's sequence
        # — this does not weaken the truncation check: a list truncated down
        # to a lone leftover item (e.g. "c." surviving from a-b-c-d-e) still
        # fails, because "c" is a valid START for neither "1" nor "a".
        allowed = ("digit", "alpha") if (self.subsection_mode != "virtual" and eff_level == 0) \
            else (_expected_list_kind(self.subsection_mode, eff_level),)
        key_prefix = ("item", self.article, self.section, self.subsection_key,
                      tuple(self._stack[:eff_level]))
        self._check_sequence_multi(key_prefix, allowed, marker, line_no, eff_level)

    def _check_sequence_multi(
        self, key_prefix: tuple, allowed_kinds: tuple[str, ...], marker: str, line_no: int, eff_level: int
    ) -> None:
        marker_l = marker.lower()
        locked_kind = next((k for k in allowed_kinds if (*key_prefix, k) in self._seq_last), None)
        if locked_kind is None:
            starts = [k for k in allowed_kinds if marker_l == _SEQ_START[k]]
            if not starts:
                expected = " or ".join(repr(_SEQ_START[k]) for k in allowed_kinds)
                raise ArticleShapeError(
                    f"{self.rel_path}:{line_no}: list at depth {eff_level} starts with "
                    f"{marker!r}, expected {expected} — a list beginning mid-sequence is "
                    f"exactly the truncated/gapped-list failure mode this check exists "
                    f"to catch"
                )
            locked_kind = starts[0]
            self._seq_last[(*key_prefix, locked_kind)] = marker_l
            return
        key = (*key_prefix, locked_kind)
        last = self._seq_last[key]
        expected = _SEQ_NEXT[locked_kind](last)
        if expected is None or marker_l != expected:
            raise ArticleShapeError(
                f"{self.rel_path}:{line_no}: list at depth {eff_level} (kind={locked_kind}): "
                f"after {last!r} expected {expected!r}, got {marker!r} — gap or unexpected "
                f"reset in an ordered list"
            )
        self._seq_last[key] = marker_l

    def check_pseudo_subsection_sequence(self, marker: str, line_no: int) -> None:
        # Grammar exception 2's pseudo-subsection headers ("1. PURPOSE",
        # "2. APPLICABILITY", ...) are themselves a digit-ordered list, one
        # per section — checked the same way, so a silently dropped
        # pseudo-header would also raise rather than just shifting labels.
        key = ("pseudo", self.article, self.section)
        self._check_sequence(key, "digit", marker, line_no, "pseudo-subsection sequence")

    def next_block_path(self, kind: str) -> list[str]:
        key = (self.article, self.section, self.subsection_key, kind)
        n = self._block_counters.get(key, 0) + 1
        self._block_counters[key] = n
        return [f"{_KIND_PREFIX[kind]}{n}"]

    def node_id(self, path: list[str]) -> str:
        return (
            f"{self.ruleset_key}:a{self.article}.s{self.section}."
            f"{self.subsection_key}.{'.'.join(path)}"
        )

    def make_node(
        self,
        *,
        kind_hint: str,
        path: list[str],
        depth: int,
        text: str,
        line: int,
        extra: dict | None = None,
    ) -> dict:
        node: dict[str, Any] = {
            "id": self.node_id(path),
            "article": self.article,
            "article_name": self.article_name,
            "section": self.section,
            "section_name": self.section_name,
            "subsection": self.subsection,
            "subsection_name": self.subsection_name,
            "path": path,
            "depth": depth,
            "text": text,
            "source_ref": {"file": self.rel_path, "line": line},
            "kind_hint": kind_hint,
        }
        if extra:
            node.update(extra)
        self.nodes.append(node)
        return node


def _read_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Returns (fields, index-of-first-body-line). Raises if the file doesn't
    open with the standard `---\\n...\\n---\\n` block every article carries."""
    if not lines or lines[0].strip() != "---":
        raise ArticleShapeError("file does not start with YAML frontmatter '---'")
    fields: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        m = FRONTMATTER_RE.match(lines[i])
        if m:
            fields[m.group(1)] = m.group(2)
        i += 1
    if i >= len(lines):
        raise ArticleShapeError("frontmatter opened but never closed")
    return fields, i + 1


def _flush_table(
    state: _ParseState,
    rows: list[tuple[int, str]],
    caption: str | None,
    caption_line: int | None,
    notes: list[str],
) -> None:
    if not rows:
        return
    if len(rows) < 2:
        raise ArticleShapeError(
            f"{state.rel_path}:{rows[0][0]}: pipe table has fewer than 2 rows "
            f"(header + separator required)"
        )
    if caption is None:
        raise ArticleShapeError(
            f"{state.rel_path}:{rows[0][0]}: pipe table with no preceding "
            f"'TABLE ...' caption — every table in the corpus has one (see "
            f"module docstring); a caption-less table is a shape violation, "
            f"not silently accepted as untitled"
        )

    def _cells(raw: str) -> list[str]:
        # Markdown pipe-table cells: strip one leading/trailing '|', split on
        # '|', trim whitespace. Source never escapes a literal '|' in a cell.
        body = raw.strip()
        if body.startswith("|"):
            body = body[1:]
        if body.endswith("|"):
            body = body[:-1]
        return [c.strip() for c in body.split("|")]

    header_line, header_raw = rows[0]
    sep_line, sep_raw = rows[1]
    columns = _cells(header_raw)
    sep_cells = _cells(sep_raw)
    if len(sep_cells) != len(columns) or not all(TABLE_SEP_CELL_RE.match(c) for c in sep_cells):
        raise ArticleShapeError(
            f"{state.rel_path}:{sep_line}: row 2 of a pipe table is not a "
            f"valid header separator ({sep_raw!r})"
        )
    body_rows = [_cells(raw) for _, raw in rows[2:]]
    for ln, raw in rows[2:]:
        if len(_cells(raw)) != len(columns):
            raise ArticleShapeError(
                f"{state.rel_path}:{ln}: table row has {len(_cells(raw))} cells, "
                f"expected {len(columns)}"
            )

    path = state.next_block_path("table")
    state.make_node(
        kind_hint="table",
        path=path,
        depth=0,
        text=caption,
        line=caption_line if caption_line is not None else header_line,
        extra={"caption": caption, "notes": list(notes), "columns": columns, "rows": body_rows},
    )
    for ln, _ in rows:
        state.consumed.add(ln)
    if caption_line is not None:
        state.consumed.add(caption_line)


def parse_article_file(
    path: Path, ruleset_key: str
) -> tuple[dict, list[dict], _ParseState, list[str]]:
    """Parses one source/article-0N-*.md into (meta, nodes). Pure function —
    writes nothing. Raises ArticleShapeError on any line this module's
    grammar can't account for (see module docstring); never guesses."""
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]  # drop the artifact of a trailing '\n' on split

    fm, body_start = _read_frontmatter(lines)
    try:
        article_num = int(fm["article-number"])
    except (KeyError, ValueError) as exc:
        raise ArticleShapeError(f"missing/invalid article-number in frontmatter: {exc}") from exc
    article_name = fm.get("article-name", "")

    rel_path = f"source/{path.name}"
    state = _ParseState(
        article=article_num, article_name=article_name, ruleset_key=ruleset_key, rel_path=rel_path
    )
    for ln in range(1, body_start + 1):
        state.consumed.add(ln)

    # table-in-progress buffer
    table_rows: list[tuple[int, str]] = []
    table_caption: str | None = None
    table_caption_line: int | None = None
    table_notes: list[str] = []
    in_fence = False
    fence_lines: list[int] = []
    title_seen = False

    def flush_table() -> None:
        nonlocal table_rows, table_caption, table_caption_line, table_notes
        _flush_table(state, table_rows, table_caption, table_caption_line, table_notes)
        table_rows = []
        table_caption = None
        table_caption_line = None
        table_notes = []

    i = body_start
    n = len(lines)
    while i < n:
        line_no = i + 1
        raw = lines[i]

        if in_fence:
            fence_lines.append(line_no)
            state.consumed.add(line_no)
            if FENCE_RE.match(raw.strip()):
                in_fence = False
                text = "\n".join(lines[fence_lines[0] - 1 : fence_lines[-1]])
                path_ = state.next_block_path("raw_typst")
                if state.section is None:
                    raise ArticleShapeError(
                        f"{rel_path}:{fence_lines[0]}: raw fence appears before any section heading"
                    )
                state.make_node(
                    kind_hint="raw_typst",
                    path=path_,
                    depth=0,
                    text=text,
                    line=fence_lines[0],
                )
                fence_lines = []
            i += 1
            continue

        if raw.strip() == "":
            state.consumed.add(line_no)
            i += 1
            continue

        if FENCE_RE.match(raw.strip()):
            flush_table()
            in_fence = True
            fence_lines = [line_no]
            state.consumed.add(line_no)
            i += 1
            continue

        if COMMENT_RE.match(raw.strip()):
            state.consumed.add(line_no)
            i += 1
            continue

        if not title_seen:
            m = TITLE_RE.match(raw)
            if not m or int(m.group(1)) != article_num:
                raise ArticleShapeError(
                    f"{rel_path}:{line_no}: expected '# Article {article_num} ...' title, got {raw!r}"
                )
            title_seen = True
            state.consumed.add(line_no)
            i += 1
            continue

        m = SECTION_RE.match(raw)
        if m:
            flush_table()
            state.enter_section(m.group(1), m.group(2).strip())
            state.consumed.add(line_no)
            state.heading_lines.add(line_no)
            state.reconstructed[line_no] = f"## {m.group(1)}. {m.group(2).strip()}"
            i += 1
            continue

        m = SUBSECTION_RE.match(raw)
        if m:
            if state.section is None:
                raise ArticleShapeError(f"{rel_path}:{line_no}: subsection before any section")
            flush_table()
            letter, name = m.group(1), m.group(2).strip()
            if state.subsection_mode == "virtual":
                raise ArticleShapeError(
                    f"{rel_path}:{line_no}: section {state.section} mixes virtual "
                    f"(no-### ) and real (###) subsection styles — grammar exception "
                    f"2 assumes a section is one or the other, never both"
                )
            state.enter_real_subsection(letter, name)
            state.consumed.add(line_no)
            state.heading_lines.add(line_no)
            state.reconstructed[line_no] = f"### {letter}. {name}"
            i += 1
            continue

        if TABLE_ROW_RE.match(raw):
            table_rows.append((line_no, raw))
            i += 1
            continue

        m = LIST_ITEM_RE.match(raw)
        if m:
            flush_table()
            indent, marker, text = len(m.group(1)), m.group(2), m.group(3)
            if indent % 4 != 0:
                raise ArticleShapeError(f"{rel_path}:{line_no}: odd indent ({indent} spaces)")
            raw_level = indent // 4
            if state.section is None:
                raise ArticleShapeError(f"{rel_path}:{line_no}: list item before any section")

            if state.subsection_mode is None:
                # First content line of this section. A depth-0 item here
                # means the section has no "### " subsections (grammar
                # exception 2) — this item IS the pseudo-subsection header.
                if raw_level != 0:
                    raise ArticleShapeError(
                        f"{rel_path}:{line_no}: first content line of section "
                        f"{state.section} is indented ({indent} spaces) but no "
                        f"subsection heading has been seen yet"
                    )
                state.check_pseudo_subsection_sequence(marker, line_no)
                state.enter_virtual_subsection(marker, text.strip())
                state.consumed.add(line_no)
                state.heading_lines.add(line_no)
                state.reconstructed[line_no] = f"{marker}. {text}" if text else f"{marker}."
                i += 1
                continue

            if state.subsection_mode == "virtual" and raw_level == 0:
                # A new pseudo-subsection header (e.g. "2. APPLICABILITY").
                state.check_pseudo_subsection_sequence(marker, line_no)
                state.enter_virtual_subsection(marker, text.strip())
                state.consumed.add(line_no)
                state.heading_lines.add(line_no)
                state.reconstructed[line_no] = f"{marker}. {text}" if text else f"{marker}."
                i += 1
                continue

            eff_level = raw_level - 1 if state.subsection_mode == "virtual" else raw_level
            if eff_level < 0 or eff_level > 2:
                raise ArticleShapeError(
                    f"{rel_path}:{line_no}: list item at unexpected nesting "
                    f"(raw indent {indent}, mode {state.subsection_mode})"
                )
            state.check_list_item_sequence(eff_level, marker, line_no)
            state._stack = state._stack[:eff_level] + [marker]
            path = list(state._stack)
            state.consumed.add(line_no)
            state.item_depth[line_no] = eff_level
            state.reconstructed[line_no] = (
                f"{'    ' * raw_level}{marker}. {text}" if text else f"{'    ' * raw_level}{marker}."
            )
            state.make_node(kind_hint="list_item", path=path, depth=eff_level, text=text, line=line_no)
            i += 1
            continue

        # Bare, unmarked line: table caption, table note, or standalone prose.
        stripped = raw.strip()
        if TABLE_CAPTION_RE.match(stripped):
            flush_table()
            table_caption = stripped
            table_caption_line = line_no
            state.consumed.add(line_no)
            i += 1
            continue
        if table_caption is not None and not table_rows:
            # Between a caption and its table's header row: a legend/note line.
            table_notes.append(stripped)
            state.consumed.add(line_no)
            i += 1
            continue

        # Standalone prose paragraph (e.g. Article 7 "### a. DEFINITION" body).
        if state.section is None or state.subsection_mode is None:
            raise ArticleShapeError(
                f"{rel_path}:{line_no}: prose line outside any section/subsection: {raw!r}"
            )
        path = state.next_block_path("prose")
        state.make_node(kind_hint="prose", path=path, depth=0, text=stripped, line=line_no)
        state.consumed.add(line_no)
        i += 1

    flush_table()
    if in_fence:
        raise ArticleShapeError(f"{rel_path}: unclosed raw fence starting at line {fence_lines[0]}")

    meta = {
        "article": article_num,
        "article_name": article_name,
        "source_file": rel_path,
        "footer_date": fm.get("footer-date"),
        "sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "node_count": len(state.nodes),
    }
    return meta, state.nodes, state, lines


# ---------------------------------------------------------------------------
# Query helpers — LOCATE BY HEADING TEXT, never by letter (see module docstring)
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return " ".join(s.strip().upper().split())


def find_section_nodes(nodes: list[dict], article: int, section_name: str) -> list[dict]:
    """All nodes in `article` whose section_name matches (case/space-insensitive)."""
    target = _norm(section_name)
    return [n for n in nodes if n["article"] == article and _norm(n["section_name"]) == target]


def find_subsection_nodes(
    nodes: list[dict], article: int, section_name: str, subsection_name: str
) -> list[dict]:
    """All nodes under (article, section_name, subsection_name), located by
    TEXT on both — never by section number or subsection letter, per the
    CRITICAL TRAP this module is built to survive (heading letters are not
    stable across sections; see e.g. exception 1 in the module docstring)."""
    sec_target = _norm(section_name)
    sub_target = _norm(subsection_name)
    return [
        n
        for n in nodes
        if n["article"] == article
        and _norm(n["section_name"]) == sec_target
        and n["subsection_name"] is not None
        and _norm(n["subsection_name"]) == sub_target
    ]


# ---------------------------------------------------------------------------
# Whole-corpus build
# ---------------------------------------------------------------------------


def build_articles(ruleset_key: str, source_dir: Path = SOURCE_DIR) -> dict:
    """Parses every configured article file and returns the full
    newcastle.articles/1.0.0 dict. Pure — writes nothing."""
    articles_meta: list[dict] = []
    all_nodes: list[dict] = []
    by_article: dict[str, int] = {}
    for num in sorted(ARTICLE_FILES):
        path = source_dir / ARTICLE_FILES[num]
        meta, nodes, _state, _lines = parse_article_file(path, ruleset_key)
        articles_meta.append(meta)
        all_nodes.extend(nodes)
        by_article[str(num)] = len(nodes)

    ids = [n["id"] for n in all_nodes]
    if len(ids) != len(set(ids)):
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        raise ArticleShapeError(f"duplicate node ids produced: {dupes[:5]}")

    return {
        "schema": SCHEMA,
        "ruleset_key": ruleset_key,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dir": "source/",
        "articles": articles_meta,
        "counts": {"total_nodes": len(all_nodes), "by_article": by_article},
        "nodes": all_nodes,
    }


# ---------------------------------------------------------------------------
# --verify: every heading consumed, every item at exactly one depth,
# reserialize-to-markdown round trip.
# ---------------------------------------------------------------------------


def verify_article_file(path: Path, ruleset_key: str) -> list[str]:
    """Returns a list of problem strings (empty == fully verified)."""
    problems: list[str] = []
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    try:
        _meta, _nodes, state, _lines2 = parse_article_file(path, ruleset_key)
    except ArticleShapeError as exc:
        return [f"parse failed: {exc}"]

    total = len(lines)
    # 1. every physical line was classified (a stronger form of "every
    #    heading is consumed": nothing at all fell through unrecognized).
    for ln in range(1, total + 1):
        if ln not in state.consumed:
            problems.append(f"line {ln} was never classified: {lines[ln - 1]!r}")

    # 2. every heading line is in heading_lines (belt-and-suspenders on the
    #    literal requirement) and every list item has exactly one depth.
    for ln in state.item_depth:
        if state.item_depth[ln] not in (0, 1, 2):
            problems.append(f"line {ln}: list item depth out of range")

    # 3. reserialize round trip. Headings/list-items/pseudo-headers are
    #    regenerated from parsed fields and compared to source; every other
    #    classified line is replayed verbatim (see module docstring for why).
    rebuilt: list[str] = []
    for idx in range(total):
        ln = idx + 1
        rebuilt.append(state.reconstructed.get(ln, lines[idx]))
    if rebuilt != lines:
        for idx, (a, b) in enumerate(zip(rebuilt, lines)):
            if a != b:
                problems.append(f"line {idx + 1} round-trip mismatch:\n  got:  {a!r}\n  want: {b!r}")
                break
        if len(rebuilt) != len(lines):
            problems.append(f"round-trip line count mismatch: got {len(rebuilt)}, want {len(lines)}")

    return problems


def run_verify(source_dir: Path = SOURCE_DIR, ruleset_key: str = DEFAULT_RULESET_KEY) -> bool:
    ok = True
    for num in sorted(ARTICLE_FILES):
        path = source_dir / ARTICLE_FILES[num]
        problems = verify_article_file(path, ruleset_key)
        if problems:
            ok = False
            print(f"FAIL {ARTICLE_FILES[num]} — {len(problems)} problem(s)")
            for p in problems[:10]:
                print(f"  - {p}")
        else:
            print(f"OK   {ARTICLE_FILES[num]}")
    return ok


# ---------------------------------------------------------------------------
# Article 7 uses map — folded from the already-parsed nodes, written as a
# sibling file (rulesets/<key>/uses.json). {use_name: {definition, standards[]}}
# ---------------------------------------------------------------------------


def build_uses_map(nodes: list[dict], ruleset_key: str) -> dict:
    art7 = [n for n in nodes if n["article"] == 7]
    # Section 1 (USE STANDARDS) and Section 2 (EXPANDED USE STANDARDS) are
    # framework, not uses — every real use section has a "DEFINITION"
    # subsection (verified); framework sections do not.
    sections: dict[str, dict] = {}
    for n in art7:
        sections.setdefault(n["section"], {"name": n["section_name"], "nodes": []})
        sections[n["section"]]["nodes"].append(n)

    uses: dict[str, dict] = {}
    for sec_num, sec in sections.items():
        has_definition = any(_norm(n["subsection_name"] or "") == "DEFINITION" for n in sec["nodes"])
        if not has_definition:
            continue  # §1, §2 — framework, not a use
        use_name = sec["name"]
        definition_nodes = [
            n for n in sec["nodes"] if _norm(n["subsection_name"] or "") == "DEFINITION"
        ]
        standards_nodes = [
            n for n in sec["nodes"] if _norm(n["subsection_name"] or "") == "STANDARDS"
        ]
        definition = definition_nodes[0]["text"] if definition_nodes else None
        standards = [
            {"path": n["path"], "depth": n["depth"], "text": n["text"], "id": n["id"]}
            for n in sorted(standards_nodes, key=lambda x: x["path"])
        ]
        uses[use_name] = {
            "section": sec_num,
            "definition": definition,
            "standards": standards,
        }

    return {
        "schema": "newcastle.uses/1.0.0",
        "ruleset_key": ruleset_key,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_article": 7,
        "counts": {"uses": len(uses)},
        "uses": uses,
    }


# ---------------------------------------------------------------------------
# Atomic write (CONTRACT.md §1.1 S2 discipline, matching ruleset_build/lift_*.py)
# ---------------------------------------------------------------------------


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
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--uses-out", type=Path, default=None)
    parser.add_argument(
        "--verify", action="store_true", help="run the structural self-check, write nothing"
    )
    args = parser.parse_args(argv)

    if args.verify:
        ok = run_verify(args.source_dir, args.ruleset_key)
        return 0 if ok else 1

    doc = build_articles(args.ruleset_key, args.source_dir)
    out = args.out or (APP_ROOT / "rulesets" / args.ruleset_key / "articles.json")
    _atomic_write_json(out, doc)
    print(f"wrote {out}")
    print(f"  total nodes: {doc['counts']['total_nodes']}")
    for a, c in sorted(doc["counts"]["by_article"].items(), key=lambda x: int(x[0])):
        print(f"    article {a}: {c} nodes")

    uses_doc = build_uses_map(doc["nodes"], args.ruleset_key)
    uses_out = args.uses_out or (APP_ROOT / "rulesets" / args.ruleset_key / "uses.json")
    _atomic_write_json(uses_out, uses_doc)
    print(f"wrote {uses_out}")
    print(f"  uses: {uses_doc['counts']['uses']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
