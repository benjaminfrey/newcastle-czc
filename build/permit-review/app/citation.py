"""Implements CONTRACT.md §5 (the citation contract).

THE ONLY citation renderer in the app. Citations are rendered from a
structured `Citation` dataclass — never from a stored string, never from
model output (§5.1). Rendering is pure and deterministic: the same struct
plus the same style always produces the same bytes (§5.1).

Nothing else in this project may define `RENUM_ADOPTED_TO_DRAFT` or render
citation text; `engine/` and `llm/` (later workflows) MUST pass a `Citation`
struct through here rather than emitting citation-shaped strings themselves
(§5.1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Literal

from app.config import RULESETS_DIR

# --------------------------------------------------------------------------- #
# §5.3 — article renumbering, seeded verbatim from extract/verso.py:18
# --------------------------------------------------------------------------- #

RENUM_ADOPTED_TO_DRAFT: dict[int, int] = {1: 1, 2: 2, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}
RENUM_DRAFT_TO_ADOPTED: dict[int, int] = {v: k for k, v in RENUM_ADOPTED_TO_DRAFT.items()}
# Draft Article 3 (Thoroughfares) is new — it has no adopted counterpart, so it is
# deliberately absent from RENUM_DRAFT_TO_ADOPTED rather than mapped to anything.

Scheme = Literal["adopted", "draft"]
Style = Literal["long", "short", "inline"]


class NoCounterpart(Exception):
    """Raised by to_scheme()/in_scheme() when an article has no counterpart in
    the target numbering scheme (draft Article 3, Thoroughfares, has no adopted
    counterpart — CONTRACT.md §5.3)."""


# --------------------------------------------------------------------------- #
# §5.2 — the struct
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Citation:
    ruleset_key: str  # "adopted"
    scheme: str  # "adopted" | "draft"  -- which numbering `article` is in
    article: int  # article number IN `scheme`
    section: str | None = None  # "5", "5.D", "7.F"  -- preserved verbatim across schemes
    subsection: str | None = None
    district_key: str | None = None  # "d1"
    district_code: str | None = None  # "D1"
    district_name: str | None = None  # "Rural"
    panel_title: str | None = None  # "PRIMARY BUILDING PLACEMENT"
    label: str | None = None  # "Side Setback"
    use_label: str | None = None  # "Residence"
    exhibit: str | None = None  # "3.1"
    table: str | None = None  # "3.5"

    # --- render_citation() only (ruleset_build/crosswalk.py's article-map-
    # aware renderer, below) -- NOT used by the original render()/§5.5
    # goldens. Reproduce the real, observed citation forms verbatim:
    #   "Article 6 Use Standards, Section 53. Residence"      (section_title)
    #   "Article 7, Section 12, Standard n. (Flood Areas)"    (standard_letter/_title)
    #   "Table 7.1 Notices & Public Hearings"                 (table_title)
    section_title: str | None = None  # "Residence" (the ## heading text, section-level only)
    standard_letter: str | None = None  # "n" -- a lettered standard NESTED inside a subsection
    standard_title: str | None = None  # "Flood Areas" -- its parenthetical short title
    table_title: str | None = None  # "Notices & Public Hearings"


def _title(s: str | None) -> str:
    """Verbatim source strings are usually ALL CAPS ('LOT DIMENSIONS'); citation
    prose wants title case ('Lot Dimensions'). A pure, deterministic transform —
    not a re-parse of source, just a display transform of an already-loaded
    string (§5.1)."""
    if not s:
        return ""
    return s.title()


# --------------------------------------------------------------------------- #
# §5.4 — rendering
# --------------------------------------------------------------------------- #


def render(c: Citation, *, style: str = "long") -> str:
    """Implements CONTRACT.md §5.4/§5.5. Pure function of `c` and `style`."""
    if style == "long":
        return _render_long(c)
    if style == "short":
        return _render_short(c)
    if style == "inline":
        return _render_inline(c)
    raise ValueError(f"citation.render: unknown style {style!r} (expected long|short|inline)")


def _district_part_long(c: Citation) -> str:
    part = c.district_code or ""
    if c.district_name:
        part = f"{part}-{c.district_name}" if part else c.district_name
    return part


def _render_long(c: Citation) -> str:
    base = f"Article {c.article}"

    if c.section:
        sec = f"Section {c.section}"
        if c.subsection:
            sec = f"{sec}.{c.subsection}"
        return f"{base}, {sec}"

    if c.district_code or c.district_name:
        out = f"{base}, {_district_part_long(c)} District"
        if c.panel_title and c.label:
            out += f", {_title(c.panel_title)}: {c.label}"
        elif c.label:
            out += f", {c.label}"
        elif c.use_label:
            out += f", {c.use_label} Use"
        return out

    if c.exhibit:
        return f"{base}, Exhibit {c.exhibit}"

    if c.table:
        return f"{base}, Table {c.table}"

    return base


def _render_short(c: Citation) -> str:
    base = f"Art. {c.article}"

    if c.section:
        sec = f"Sec. {c.section}"
        if c.subsection:
            sec = f"{sec}.{c.subsection}"
        return f"{base}, {sec}"

    if c.district_code:
        out = f"{base}, {c.district_code}"
        if c.label:
            out += f", {c.label}"
        elif c.use_label:
            out += f", {c.use_label}"
        return out

    if c.exhibit:
        return f"{base}, Ex. {c.exhibit}"

    if c.table:
        return f"{base}, Tbl. {c.table}"

    return base


def _render_inline(c: Citation) -> str:
    """A compact, parenthetical-friendly form. Not covered by a §5.5 golden
    string; kept consistent with the long/short rules above."""
    if c.section:
        sec = c.section + (f".{c.subsection}" if c.subsection else "")
        return f"Art. {c.article} §{sec}"

    if c.district_code:
        tail = c.label or (f"{c.use_label} Use" if c.use_label else None)
        return f"{c.district_code}" + (f" {tail}" if tail else "")

    if c.exhibit:
        return f"Ex. {c.exhibit}"

    if c.table:
        return f"Tbl. {c.table}"

    return f"Art. {c.article}"


# --------------------------------------------------------------------------- #
# §5.3 — scheme conversion
# --------------------------------------------------------------------------- #


def to_scheme(article: int, *, frm: str, to: str) -> int:
    """Section numbers are preserved; only article numbers shift (§5.3)."""
    if frm not in ("adopted", "draft") or to not in ("adopted", "draft"):
        raise ValueError(f"citation.to_scheme: scheme must be 'adopted' or 'draft', got frm={frm!r} to={to!r}")
    if frm == to:
        return article
    table = RENUM_ADOPTED_TO_DRAFT if (frm, to) == ("adopted", "draft") else RENUM_DRAFT_TO_ADOPTED
    if article not in table:
        raise NoCounterpart(
            f"{frm} Article {article} has no {to} counterpart "
            f"({'draft Article 3, Thoroughfares, is new' if frm == 'draft' and article == 3 else 'unmapped article number'})"
        )
    return table[article]


def in_scheme(c: Citation, scheme: str) -> Citation:
    """Returns a renumbered copy of `c` in `scheme`. Everything but `scheme` and
    `article` is carried through unchanged, per §5.3 (section numbers preserved)."""
    if c.scheme == scheme:
        return c
    new_article = to_scheme(c.article, frm=c.scheme, to=scheme)
    return replace(c, scheme=scheme, article=new_article)


# --------------------------------------------------------------------------- #
# article-map.json — article NAMES, keyed by scheme (ruleset_build/crosswalk.py
# builds this file; loaded here read-only, same load-once-and-cache pattern as
# app/rulesets.py). "adopted" and "draft" are the only two article_scheme
# values a case's ruleset ever carries (CONTRACT.md §4.5).
# --------------------------------------------------------------------------- #

_ARTICLE_MAP_CACHE: dict[str, Any] | None = None


class ArticleMapNotFound(LookupError):
    """rulesets/article-map.json hasn't been built yet. Run
    `python -m ruleset_build.crosswalk` (ruleset_build/crosswalk.py)."""


def _load_article_map() -> dict[str, Any]:
    global _ARTICLE_MAP_CACHE
    if _ARTICLE_MAP_CACHE is None:
        path = RULESETS_DIR / "article-map.json"
        if not path.exists():
            raise ArticleMapNotFound(
                f"{path} does not exist -- run `python -m ruleset_build.crosswalk` "
                f"to build it before calling article_name()/render_citation()."
            )
        with path.open("r", encoding="utf-8") as f:
            _ARTICLE_MAP_CACHE = json.load(f)
    return _ARTICLE_MAP_CACHE


def article_name(scheme: str, article: int) -> str | None:
    """The display name for `article` in `scheme` ("Use Standards", "Administration",
    ...), from rulesets/article-map.json. None if the article number is absent from
    that scheme's map (should not happen for a valid Citation -- to_scheme()/
    in_scheme() would already have raised NoCounterpart first)."""
    m = _load_article_map()
    side = m.get(scheme)
    if not side:
        raise ValueError(f"citation.article_name: unknown scheme {scheme!r} (expected 'adopted' or 'draft')")
    entry = side.get(str(article))
    return entry.get("name") if entry else None


def clear_article_map_cache() -> None:
    """Test-only: drop the cached article-map.json so a subsequent
    article_name()/render_citation() call re-reads disk."""
    global _ARTICLE_MAP_CACHE
    _ARTICLE_MAP_CACHE = None


# --------------------------------------------------------------------------- #
# render_citation() — renders a Citation in a CASE's ruleset numbering,
# reproducing the real citation forms observed in
# docs/Findings of Fact and Conclusions of Law/ verbatim (see the four forms
# named on the Citation dataclass's `section_title`/`standard_letter`/
# `standard_title`/`table_title` fields, above). NEVER accepts a
# pre-formatted string -- every character comes from `c`'s structured
# fields plus the article name looked up from article-map.json.
#
# The one governing rule, derived from the real decisions (verified against
# all four required forms): the article NAME is shown only at the coarse
# end of the citation -- an article alone, or an article + a bare numbered
# section -- and dropped once the citation gets specific enough to name a
# subsection letter or a lettered standard. A local ordinance NEVER takes a
# section symbol (CONTRACT.md §5's citations, matching the real decisions'
# "Section 12" / "Sec. 3.B.", never "§12").
# --------------------------------------------------------------------------- #


def render_citation(c: Citation, *, scheme: str, style: str = "long") -> str:
    """Renders `c` in `scheme`'s numbering (converting the article number via
    to_scheme()/in_scheme() -- raises NoCounterpart for e.g. draft Article 3,
    Thoroughfares, rendered against "adopted"), using rulesets/article-map.json
    for the article name. `style` only affects the section-word abbreviation
    ("Section" vs "Sec.") -- unlike render(), there is no separate "short" vs
    "long" *shape*, because the real decisions this reproduces don't have one.
    """
    if style not in ("long", "short"):
        raise ValueError(f"citation.render_citation: unknown style {style!r} (expected long|short)")

    target = in_scheme(c, scheme)
    name = article_name(scheme, target.article)
    sec_word = "Section" if style == "long" else "Sec."

    if target.table:
        return f"Table {target.table} {target.table_title}" if target.table_title else f"Table {target.table}"

    if target.exhibit:
        return f"Exhibit {target.exhibit}"

    if not target.section:
        return f"Article {target.article} {name}" if name else f"Article {target.article}"

    # Granular citations (a lettered standard, or a lettered subsection) drop
    # the article name -- matches "Article 7, Section 12, Standard n. (Flood
    # Areas)" and "Article 2, Sec. 3.B. Applicability" (no name in either).
    if target.standard_letter:
        out = f"Article {target.article}, {sec_word} {target.section}, Standard {target.standard_letter}."
        if target.standard_title:
            out += f" ({target.standard_title})"
        return out

    if target.subsection:
        out = f"Article {target.article}, {sec_word} {target.section}.{target.subsection}."
        if target.section_title:
            out += f" {target.section_title}"
        return out

    # Bare "article + section" (no subsection, no standard letter) is coarse
    # enough to keep the article name -- matches "Article 6 Use Standards,
    # Section 53. Residence".
    prefix = f"Article {target.article} {name}" if name else f"Article {target.article}"
    out = f"{prefix}, {sec_word} {target.section}."
    if target.section_title:
        out += f" {target.section_title}"
    return out


# --------------------------------------------------------------------------- #
# §5.4 — Citation builders from ruleset data (districts.json / use-matrix.json shapes)
# --------------------------------------------------------------------------- #


def _district_citation_seed(district: dict[str, Any]) -> dict[str, Any]:
    """Pulls article/district_code/district_name out of a district object's own
    `citation` block (§4.1), falling back to `code`/`name` when a field is
    absent so a partially-built ruleset still renders something sane."""
    dcit = district.get("citation") or {}
    return {
        "article": dcit.get("article", 2),
        "district_code": dcit.get("district") or district.get("code"),
        "district_name": dcit.get("district_name") or _title(district.get("name")),
    }


def from_dimension(ruleset_key: str, district: dict[str, Any], dim: dict[str, Any]) -> Citation:
    """Implements CONTRACT.md §5.4. `dim` is one entry of a district's
    `dimensions[]` (§4.2)."""
    seed = _district_citation_seed(district)
    dimcit = dim.get("citation") or {}
    return Citation(
        ruleset_key=ruleset_key,
        scheme="adopted",
        article=dimcit.get("article", seed["article"]),
        district_key=district.get("district_key"),
        district_code=dimcit.get("district") or seed["district_code"],
        district_name=seed["district_name"],
        panel_title=dimcit.get("panel") or dim.get("panel_title"),
        label=dimcit.get("label") or dim.get("label"),
    )


def from_use_cell(ruleset_key: str, district: dict[str, Any], use: dict[str, Any], cell: dict[str, Any]) -> Citation:
    """Implements CONTRACT.md §5.4. `use` is one entry of `use-matrix.json`
    `uses[]`; `cell` is the matching `cells[]` entry for this district (§4.3)."""
    seed = _district_citation_seed(district)
    return Citation(
        ruleset_key=ruleset_key,
        scheme="adopted",
        article=seed["article"],
        district_key=district.get("district_key"),
        district_code=seed["district_code"],
        district_name=seed["district_name"],
        use_label=use.get("label"),
    )



# --------------------------------------------------------------------------- #
# Indefinite article
# --------------------------------------------------------------------------- #

# "a" or "an" is decided by SOUND, not spelling: "a Use Permit" (yoo-) is correct
# and "an Use Permit" is not, while "an Expanded Use Permit" is. A plain
# first-letter-is-a-vowel rule gets both of those wrong in opposite directions,
# so the yoo-sound prefixes are listed explicitly.
#
# The vocabulary this runs over is CLOSED and small (63 use labels + 4 permit
# labels in the adopted ruleset), and tests/test_use_matrix.py asserts the
# article chosen for every one of them -- so if a future ruleset introduces a
# word this rule gets wrong, a test fails rather than a worksheet going out with
# "a Office" on it.
_YOO_SOUND_PREFIXES = ("use", "uti", "uni", "ura", "ust", "eu", "ewe", "one")


def indefinite_article(phrase: str) -> str:
    """Return "a" or "an" for `phrase`, by initial sound."""
    word = (phrase or "").lstrip().lower()
    if not word:
        return "a"
    if word.startswith(_YOO_SOUND_PREFIXES):
        return "a"
    return "an" if word[0] in "aeiou" else "a"


def required_review_row(district: dict[str, Any], use: dict[str, Any], cell: dict[str, Any]) -> dict[str, Any]:
    """Implements CONTRACT.md §5.4/§5.5 — the "Required Review(s)" row: the §4.4
    legend applied to one (district, use) cell, in the exact Buehner-style
    sentence form. Always builds the sentence here, from structured fields —
    never stores or trusts a pre-written string (§5.1)."""
    ruleset_key = district.get("ruleset_key", "adopted")
    citation = from_use_cell(ruleset_key, district, use, cell)
    seed = _district_citation_seed(district)
    district_label = _district_part_long(
        replace(citation, district_code=seed["district_code"], district_name=seed["district_name"])
    )
    use_label = use.get("label", "")

    allowed = bool(cell.get("allowed"))
    permit = cell.get("permit")
    authority = cell.get("authority")

    if not allowed or not permit:
        art = indefinite_article(use_label).capitalize()
        sentence = f"{art} {use_label} use is not allowed in the {district_label} District."
        return {"permit": None, "authority": None, "sentence": sentence, "citation": citation}

    verb = "can be issued" if authority == "CEO" else "must be issued"
    art = indefinite_article(use_label).capitalize()
    permit_art = indefinite_article(permit)
    sentence = (f"{art} {use_label} use in the {district_label} District requires "
                f"{permit_art} {permit} which {verb} by the {authority}.")
    return {"permit": permit, "authority": authority, "sentence": sentence, "citation": citation}


# --------------------------------------------------------------------------- #
# §5.5 — golden strings, self-checked (also asserted by `--selftest`, S6 check 7)
# --------------------------------------------------------------------------- #


def _golden_checks() -> list[tuple[str, bool]]:
    """Returns [(description, passed), ...] for the four §5.5 golden strings.
    Used by app/main.py:selftest()."""
    results: list[tuple[str, bool]] = []

    c1 = Citation(
        "adopted", "adopted", 2,
        district_code="D1", district_name="Rural",
        panel_title="LOT DIMENSIONS", label="Primary Frontage Line Length",
    )
    results.append((
        "render(long) golden #1",
        render(c1) == "Article 2, D1-Rural District, Lot Dimensions: Primary Frontage Line Length",
    ))
    results.append((
        "render(short) golden #2",
        render(c1, style="short") == "Art. 2, D1, Primary Frontage Line Length",
    ))

    c3 = Citation("adopted", "adopted", 7, section="34", subsection="b")
    results.append((
        "render(long) golden #3",
        render(c3) == "Article 7, Section 34.b",
    ))

    d1 = {
        "district_key": "d1", "code": "D1", "name": "RURAL",
        "citation": {"article": 2, "district": "D1", "district_name": "Rural"},
        "ruleset_key": "adopted",
    }
    residence = {"use_key": "residence", "label": "Residence"}
    cell = {
        "district_key": "d1", "use_key": "residence", "code": "u",
        "permit": "Use Permit", "permit_key": "use",
        "authority": "CEO", "authority_key": "ceo", "allowed": True,
    }
    row = required_review_row(d1, residence, cell)
    results.append((
        "required_review_row golden #4",
        row["sentence"] == "A Residence use in the D1-Rural District requires a Use Permit which can be issued by the CEO.",
    ))

    return results
