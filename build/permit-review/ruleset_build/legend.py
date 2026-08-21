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

_LEGEND_HEADING_RE = re.compile(r"USE TABLE LEGEND")
_GLYPHS_RE = re.compile(r"#let\s+glyphs\s*=\s*\(([^)]*)\)")
_GLYPH_ENTRY_RE = re.compile(r'(\w+)\s*:\s*"([^"]*)"')
_ROW_RE = re.compile(
    r'status\(\s*"(?P<code>\w*)"\s*\)\s*,\s*'
    r"\[(?P<permit>[^\]]+)\]\s*,\s*"
    r"\[(?P<authority>[^\]]+)\]\s*,"
)
_NOTE_RE = re.compile(r"Note:\s*Uses without[^\]]*not allowed in this District", re.IGNORECASE)
_STATUS_CALL_RE = re.compile(r'#?status\(\s*"(\w+)"\s*\)')


class LegendParseError(RuntimeError):
    """Raised when the USE TABLE LEGEND block cannot be found or parsed, or
    when what was parsed does not match EXPECTED_LEGEND."""


def parse_legend(typ_text: str) -> list[dict]:
    """Parse the USE TABLE LEGEND block out of article-02.typ.

    Returns a list of 5 row dicts (u, rc, sp, ex, and the "" prohibited row),
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
    # generic renderer used elsewhere) for the four literal legend rows.
    tail = typ_text[heading_match.end() :]
    rows: list[dict] = []
    seen_codes: set[str] = set()
    for m in _ROW_RE.finditer(tail):
        code = m.group("code")
        if not code or code in seen_codes:
            continue
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
                "authority_key": slug(authority),
                "glyph": glyphs[code],
                "allowed": True,
            }
        )
        if len(seen_codes) == len(_REQUIRED_CODES):
            break

    found_codes = {r["code"] for r in rows}
    missing = [c for c in _REQUIRED_CODES if c not in found_codes]
    if missing:
        raise LegendParseError(
            f"USE TABLE LEGEND block did not yield rows for: {missing} "
            f"(found: {sorted(found_codes)})"
        )
    rows.sort(key=lambda r: _REQUIRED_CODES.index(r["code"]))  # canonical order

    note_match = _NOTE_RE.search(tail)
    if not note_match:
        raise LegendParseError(
            "could not find the legend's 'Note: Uses without ...' sentence"
        )
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
    for expected in EXPECTED_LEGEND:
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
