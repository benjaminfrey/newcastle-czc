"""Implements CONTRACT.md §4.4 (the use-status legend) for
ruleset_build/build_use_matrix.py.

Parses the "USE TABLE LEGEND" block out of source/article-02.typ instead of
hard-coding the four rows, so a future edit to that block is picked up on the
next build rather than silently going stale. The parsed result is then
asserted against EXPECTED_LEGEND (the CONTRACT.md §4.4 table) as a sanity
check — a mismatch is a hard failure, never a silent drift.
"""

from __future__ import annotations

import re

from ruleset_build.slugs import slug

# The documented mapping (CONTRACT.md §4.4). Used ONLY to sanity-check what
# was actually parsed out of the .typ — never as the source of the output.
EXPECTED_LEGEND: list[dict] = [
    {
        "code": "u",
        "permit": "Use Permit",
        "permit_key": "use",
        "authority": "CEO",
        "authority_key": "ceo",
        "glyph": "●",
        "allowed": True,
    },
    {
        "code": "rc",
        "permit": "Residential Companion Permit",
        "permit_key": "residential_companion",
        "authority": "CEO",
        "authority_key": "ceo",
        "glyph": "❶",
        "allowed": True,
    },
    {
        "code": "sp",
        "permit": "Special Permit",
        "permit_key": "special",
        "authority": "Planning Board",
        "authority_key": "planning_board",
        "glyph": "❷",
        "allowed": True,
    },
    {
        "code": "ex",
        "permit": "Expanded Use Permit",
        "permit_key": "expanded_use",
        "authority": "Planning Board",
        "authority_key": "planning_board",
        "glyph": "✪",
        "allowed": True,
    },
    {
        "code": "",
        "permit": None,
        "permit_key": "prohibited",
        "authority": None,
        "authority_key": None,
        "glyph": None,
        "allowed": False,
        "note": "Uses without u, rc, sp, or ex are not allowed in this District.",
    },
]

_REQUIRED_CODES = ("u", "rc", "sp", "ex")
# Right to Farm (plans/2026-10-14-right-to-farm-plan-a-status-code.md, R1-R4):
# a fifth, permit-free status. Optional, so the v1.0 tag's four-code legend
# still parses for redlines against the baseline.
_OPTIONAL_CODES = ("br",)
_CANONICAL_ORDER = _REQUIRED_CODES + _OPTIONAL_CODES

EXPECTED_BR_ROW: dict = {
    "code": "br",
    "permit": "No Permit",
    "permit_key": "no",
    "authority": "—",
    "authority_key": None,
    "glyph": "○",
    "allowed": True,
}
NOTE_WITH_BR = ("Uses without u, rc, sp, ex, or br are not allowed in this District. "
                "Uses marked br require no permit but must meet the standards of "
                "Article 7 Section 3.")

_LEGEND_HEADING_RE = re.compile(r"USE TABLE LEGEND")
_GLYPHS_RE = re.compile(r"#let\s+glyphs\s*=\s*\(([^)]*)\)")
_GLYPH_ENTRY_RE = re.compile(r'(\w+)\s*:\s*"([^"]*)"')
_ROW_RE = re.compile(
    r'status\(\s*"(?P<code>\w*)"\s*\)\s*,\s*'
    r"\[(?P<permit>[^\]]+)\]\s*,\s*"
    r"\[(?P<authority>[^\]]+)\]\s*,"
)
# To the Note's closing bracket: with `br` the Note has a second sentence.
_NOTE_RE = re.compile(r"Note:\s*Uses without[^\]]*", re.IGNORECASE)
_STATUS_CALL_RE = re.compile(r'#?status\(\s*"(\w+)"\s*\)')


class LegendParseError(RuntimeError):
    """Raised when the USE TABLE LEGEND block cannot be found or parsed, or
    when what was parsed does not match EXPECTED_LEGEND."""


def parse_legend(typ_text: str) -> list[dict]:
    """Parse the USE TABLE LEGEND block out of article-02.typ.

    Returns 5 row dicts (u, rc, sp, ex, and the "" prohibited row), or 6 when
    the legend carries the optional `br` row, in the order u, rc, sp, ex, br, "";
    each: {code, permit, permit_key, authority, authority_key, glyph, allowed}
    plus "note" on the prohibited row.

    Raises LegendParseError if the block is missing, if it doesn't yield rows
    for all of u/rc/sp/ex, or if the result doesn't match EXPECTED_LEGEND.
    """
    heading_match = _LEGEND_HEADING_RE.search(typ_text)
    if not heading_match:
        raise LegendParseError(
            "could not find the 'USE TABLE LEGEND' heading in article-02.typ — "
            "has the block moved or been renamed?"
        )

    glyphs_match = _GLYPHS_RE.search(typ_text)
    if not glyphs_match:
        raise LegendParseError(
            "could not find '#let glyphs = (...)' in article-02.typ"
        )
    glyphs = dict(_GLYPH_ENTRY_RE.findall(glyphs_match.group(1)))
    missing_glyphs = [c for c in _REQUIRED_CODES if c not in glyphs]
    if missing_glyphs:
        raise LegendParseError(f"glyphs dict is missing codes: {missing_glyphs}")

    # Scan forward from the heading (not the whole file — status(...) is a
    # generic renderer used elsewhere), and only up to the Note, for the
    # literal legend rows.
    tail = typ_text[heading_match.end() :]
    note_match = _NOTE_RE.search(tail)
    if not note_match:
        raise LegendParseError(
            "could not find the legend's 'Note: Uses without ...' sentence"
        )
    rows: list[dict] = []
    seen_codes: set[str] = set()
    for m in _ROW_RE.finditer(tail, 0, note_match.start()):
        code = m.group("code")
        if not code or code in seen_codes:
            continue
        if code not in _CANONICAL_ORDER:
            raise LegendParseError(
                f"USE TABLE LEGEND has an unknown status code {code!r} — "
                f"not one of {list(_CANONICAL_ORDER)}; CONTRACT.md §4.4 needs a decision first"
            )
        if code not in glyphs:
            raise LegendParseError(f"glyphs dict is missing code {code!r}")
        seen_codes.add(code)

        permit_full = " ".join(m.group("permit").split())
        authority = " ".join(m.group("authority").split())

        if not permit_full.endswith(" Required"):
            raise LegendParseError(
                f"legend row for {code!r} does not end in ' Required': {permit_full!r}"
            )
        permit = permit_full[: -len(" Required")]
        if not permit.endswith(" Permit"):
            raise LegendParseError(
                f"legend row for {code!r} permit label does not end in ' Permit': {permit!r}"
            )
        permit_key = slug(permit[: -len(" Permit")])

        rows.append(
            {
                "code": code,
                "permit": permit,
                "permit_key": permit_key,
                "authority": authority,
                "authority_key": slug(authority) or None,
                "glyph": glyphs[code],
                "allowed": True,
            }
        )

    found_codes = {r["code"] for r in rows}
    missing = [c for c in _REQUIRED_CODES if c not in found_codes]
    if missing:
        raise LegendParseError(
            f"USE TABLE LEGEND block did not yield rows for: {missing} "
            f"(found: {sorted(found_codes)})"
        )
    rows.sort(key=lambda r: _CANONICAL_ORDER.index(r["code"]))  # canonical order

    note_text = _STATUS_CALL_RE.sub(lambda m: m.group(1), note_match.group(0))
    note_text = re.sub(r"^\s*Note:\s*", "", note_text)
    note_text = " ".join(note_text.split())
    if not note_text.endswith("."):
        note_text += "."

    rows.append(
        {
            "code": "",
            "permit": None,
            "permit_key": "prohibited",
            "authority": None,
            "authority_key": None,
            "glyph": None,
            "allowed": False,
            "note": note_text,
        }
    )

    _assert_matches_expected(rows)
    return rows


def _assert_matches_expected(rows: list[dict]) -> None:
    by_code = {r["code"]: r for r in rows}
    has_br = "br" in by_code
    expected_rows = list(EXPECTED_LEGEND)
    if has_br:
        expected_rows.append(EXPECTED_BR_ROW)
        expected_rows = [dict(e, note=NOTE_WITH_BR) if e["code"] == "" else e
                         for e in expected_rows]
    for expected in expected_rows:
        actual = by_code.get(expected["code"])
        if actual is None:
            raise LegendParseError(f"parsed legend is missing code {expected['code']!r}")
        for key in expected:
            if actual.get(key) != expected[key]:
                raise LegendParseError(
                    f"parsed legend row {expected['code']!r} field {key!r} = "
                    f"{actual.get(key)!r}, expected {expected[key]!r} — "
                    f"article-02.typ's USE TABLE LEGEND changed and "
                    f"EXPECTED_LEGEND (CONTRACT.md §4.4) needs a matching update."
                )
