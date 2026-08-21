"""Implements the W2 task brief's "article map + crosswalk" deliverable
(CONTRACT.md §5.3's article renumbering, extended to section/subsection
node level).

Produces two build-output files, read-only at runtime:

  rulesets/article-map.json  -- adopted<->draft article number + name map,
      seeded from app.citation.RENUM_ADOPTED_TO_DRAFT (itself seeded from
      extract/verso.py:18 -- see CONTRACT.md §5.3). Article NAMES are read
      from each draft source/article-0N-*.md's "# Article N Name" heading;
      adopted names are the SAME strings under the mapped draft number,
      because renumbering shifts article numbers only, never names or
      section numbers (CONTRACT.md §5.3, extract/verso.py's docstring).

  rulesets/crosswalk.json    -- node-level (section, subsection) matches
      between the adopted PDF (docs/Newcastle Core Zoning Code.pdf) and the
      draft markdown (source/article-0N-*.md), for the six prose articles
      that exist on both sides: adopted {1,3,4,5,6,7} <-> draft
      {1,4,5,6,7,8}. Matched on section-NUMBER identity (verified: numbers
      are preserved across schemes -- CONTRACT.md §5.3) with a normalized
      title-similarity confidence score; NOT invented from title similarity
      alone. Two articles are deliberately OUT OF SCOPE, not silently
      dropped -- recorded in crosswalk.json's "excluded_articles":
        - adopted 2 / draft 2 (District Standards): district-keyed, not
          section/subsection prose, and rulesets/adopted/districts.json is
          deliberately BLOCKED on D-0001/D-0002 (see CONTRACT.md §4.2.3
          and DECISIONS-NEEDED.md) -- this module MUST NOT touch that file
          or work around its absence.
        - adopted 8 / draft 9 (Definitions): a flat "**Term:**\\ndefinition"
          list (272 entries), not section/subsection prose.
      Draft article 3 (Thoroughfares) has NO adopted counterpart at all
      (CONTRACT.md §5.3's NoCounterpart) and is likewise recorded, not
      matched.

Human corrections live in rulesets/crosswalk-overrides.json (seeded empty
with a _README) -- this module NEVER invents a match to force coverage;
every automatic match is anchored on section-number identity, and anything
that doesn't line up goes to the unmatched lists for a human to resolve
via the overrides file.

Usage:
    python -m ruleset_build.crosswalk [--out-dir rulesets]

Offline; reads docs/Newcastle Core Zoning Code.pdf (read-only, never
modified -- CONTRACT.md §8.1) and source/article-0N-*.md (read-only).
Writes only rulesets/article-map.json, rulesets/crosswalk.json and (if
absent) rulesets/crosswalk-overrides.json, all via the project's standard
atomic-write pattern (round-trip verify -> temp file -> os.replace ->
best-effort dir fsync), same as ruleset_build/lift_manifest.py.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent

sys.path.insert(0, str(APP_ROOT))  # so `app.*` / `ruleset_build.*` imports work when run as a script

from app.citation import (  # noqa: E402
    RENUM_ADOPTED_TO_DRAFT,
    RENUM_DRAFT_TO_ADOPTED,
)

ADOPTED_PDF_PATH = REPO_ROOT / "docs" / "Newcastle Core Zoning Code.pdf"
SOURCE_DIR = REPO_ROOT / "source"

# Prose articles that exist on BOTH sides and get node-level (section/
# subsection) matching. Keyed by ADOPTED article number.
MATCHED_ADOPTED_ARTICLES: frozenset[int] = frozenset({1, 3, 4, 5, 6, 7})

# Deliberately out of scope -- see module docstring. Not silently dropped:
# recorded in crosswalk.json's "excluded_articles".
EXCLUDED_ARTICLES: dict[str, dict[str, Any]] = {
    "adopted:2": {
        "reason": (
            "District Standards is district-keyed (13 districts x panels), not "
            "section/subsection prose. rulesets/adopted/districts.json is "
            "deliberately blocked on D-0001/D-0002 (CONTRACT.md §4.2.3, "
            "DECISIONS-NEEDED.md) -- this module does not touch it or work "
            "around its absence."
        )
    },
    "draft:2": {"reason": "Same as adopted:2 -- Article 2 is Article 2 in both schemes."},
    "adopted:8": {
        "reason": "Definitions is a flat '**Term:**\\ndefinition' list (272 entries), not section/subsection prose."
    },
    "draft:9": {"reason": "Same as adopted:8 -- Definitions, renumbered draft Article 9."},
    "draft:3": {
        "reason": "Thoroughfares is new in the draft; it has no adopted counterpart (CONTRACT.md §5.3 NoCounterpart)."
    },
}


class CrosswalkBuildError(Exception):
    """Raised when the source shape this module depends on has moved --
    fail loudly rather than silently emit an empty or partial crosswalk."""


# --------------------------------------------------------------------------- #
# small shared helpers
# --------------------------------------------------------------------------- #


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _strip_artifacts(s: str) -> str:
    """Drop the stray U+0007 bullet-glyph artifact PyMuPDF sometimes emits
    for the PDF's bulleted list markers; not a legal-content change, purely
    a text-extraction cleanup (parallels CONTRACT.md §4.3.2's D4 soft-hyphen
    merge -- mechanical, not a judgement call)."""
    return s.replace("\x07", "").strip()


def _clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", _strip_artifacts(t))


def _normalize_title(s: str) -> str:
    s = s.casefold()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na and not nb:
        return 1.0
    return round(difflib.SequenceMatcher(None, na, nb).ratio(), 4)


def _atomic_write_json(target: Path, obj: dict) -> None:
    """Same pattern as ruleset_build/lift_manifest.py: serialize -> round-trip
    verify -> temp file in the same dir -> fsync -> os.replace -> best-effort
    dir fsync."""
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError(f"round-trip verification failed before write of {target} — refusing to write")

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


# --------------------------------------------------------------------------- #
# article-map.json
# --------------------------------------------------------------------------- #

_ARTICLE_HEADING_RE = re.compile(r"^# Article (\d+) (.+)$", re.MULTILINE)


def _read_draft_article_names(source_dir: Path = SOURCE_DIR) -> tuple[dict[int, str], dict[int, str]]:
    """Returns (names, source_files) keyed by DRAFT article number, read from
    each source/article-0N-*.md's '# Article N Name' heading. Fails loudly
    if a file is missing the heading or the discovered article-number set
    doesn't match what RENUM_ADOPTED_TO_DRAFT + the new draft Article 3
    predict (CONTRACT.md §5.3)."""
    names: dict[int, str] = {}
    files: dict[int, str] = {}
    for path in sorted(source_dir.glob("article-0*-*.md")):
        text = path.read_text(encoding="utf-8")
        m = _ARTICLE_HEADING_RE.search(text)
        if not m:
            raise CrosswalkBuildError(f"{path}: no '# Article N Name' heading found in the first match window")
        num = int(m.group(1))
        if num in names:
            raise CrosswalkBuildError(f"draft article {num} heading found twice ({files[num]} and {path})")
        names[num] = m.group(2).strip()
        files[num] = str(path.relative_to(REPO_ROOT))

    expected = set(RENUM_ADOPTED_TO_DRAFT.values()) | {3}
    if set(names) != expected:
        raise CrosswalkBuildError(
            f"draft article set mismatch: found {sorted(names)}, expected {sorted(expected)} "
            f"(RENUM_ADOPTED_TO_DRAFT's range + new draft Article 3 Thoroughfares) — "
            f"source/article-0N-*.md moved or was renamed."
        )
    return names, files


def build_article_map() -> dict[str, Any]:
    """Implements the task brief's article-map.json. Adopted names are
    DERIVED from draft names via RENUM_ADOPTED_TO_DRAFT (never hand-typed a
    second time) because renumbering changes article NUMBERS only — the
    name is the same string under whichever number the scheme uses
    (CONTRACT.md §5.3, extract/verso.py's docstring)."""
    draft_names, draft_files = _read_draft_article_names()

    adopted: dict[str, Any] = {}
    for a, d in sorted(RENUM_ADOPTED_TO_DRAFT.items()):
        adopted[str(a)] = {
            "name": draft_names[d],
            "draft_counterpart": d,
            "source": "docs/Newcastle Core Zoning Code.pdf (read-only baseline)",
        }

    draft: dict[str, Any] = {}
    for d, name in sorted(draft_names.items()):
        draft[str(d)] = {
            "name": name,
            "adopted_counterpart": RENUM_DRAFT_TO_ADOPTED.get(d),  # None for draft Article 3
            "source_file": draft_files[d],
        }

    return {
        "schema": "newcastle.article-map/1.0.0",
        "generated_at": _now_iso(),
        "source": {
            "renum_owner": "app/citation.py:RENUM_ADOPTED_TO_DRAFT (seeded from extract/verso.py:18)",
            "draft_names_from": "source/article-0N-*.md '# Article N Name' headings",
        },
        "section_numbers": "preserved across schemes; only article numbers shift (CONTRACT.md §5.3)",
        "adopted_to_draft": {str(k): v for k, v in sorted(RENUM_ADOPTED_TO_DRAFT.items())},
        "draft_to_adopted": {str(k): v for k, v in sorted(RENUM_DRAFT_TO_ADOPTED.items())},
        "adopted": adopted,
        "draft": draft,
    }


# --------------------------------------------------------------------------- #
# adopted PDF section/subsection heading extraction
# --------------------------------------------------------------------------- #
#
# Grammar (measured against docs/Newcastle Core Zoning Code.pdf, mirrors the
# draft markdown grammar the task brief documents):
#   section heading    "<N>.\t<TITLE>"                    (TITLE inline, all-caps)
#   subsection heading  either "<letter>.\t<TITLE>"        (TITLE inline, all-caps)
#                        or     "<letter>.\t" alone, then 1-3 following
#                               all-caps lines are the (possibly wrapped) TITLE
# A numbered/lettered LIST ITEM (not a heading) is anything that doesn't fit
# either shape -- its body text is ordinary sentence case, so the all-caps
# test is the load-bearing discriminator. Verified against every draft
# section/subsection count for adopted articles 1,3,4,5,6: exact match;
# article 7: 29/29 sections, 139/141 subsections (two short-title-run edge
# cases not recovered -- those simply don't become adopted nodes, so they
# surface honestly as draft-side unmatched, never a fabricated match).

_SEC_RE = re.compile(r"^(\d{1,3})\.\t+\s*(\S.*)$")
_SUB_INLINE_RE = re.compile(r"^([a-z])\.\t+\s*(\S.*)$")
_BARE_LETTER_RE = re.compile(r"^([a-z])\.\t*$")


def _is_capsy(line: str, *, max_len: int = 70) -> bool:
    line = _strip_artifacts(line)
    letters = [c for c in line if c.isalpha()]
    if len(letters) < 2:
        return False
    return all(c.isupper() for c in letters) and len(line) <= max_len


def _discover_adopted_article_ranges(doc: Any) -> dict[int, tuple[int, int]]:
    """Scans every page's text for 'ARTICLE <N>' and returns the LONGEST
    contiguous run of pages for each article number, as (first, last)
    0-indexed page numbers. The longest-run rule is what separates the real
    body pages from isolated single-page false hits in the front-matter
    Table of Contents (which also contains the string 'ARTICLE 1' etc.)."""
    article_re = re.compile(r"ARTICLE\s+(\d+)")
    per_page: list[int | None] = []
    for i in range(doc.page_count):
        m = article_re.search(doc[i].get_text())
        per_page.append(int(m.group(1)) if m else None)

    runs: dict[int, list[tuple[int, int]]] = {}
    i = 0
    n = len(per_page)
    while i < n:
        art = per_page[i]
        if art is None:
            i += 1
            continue
        j = i
        while j + 1 < n and per_page[j + 1] == art:
            j += 1
        runs.setdefault(art, []).append((i, j))
        i = j + 1

    ranges: dict[int, tuple[int, int]] = {}
    for art, spans in runs.items():
        ranges[art] = max(spans, key=lambda span: span[1] - span[0])
    return ranges


def _extract_adopted_article_nodes(doc: Any, p0: int, p1: int) -> list[dict[str, Any]]:
    """Returns [{"section": "12", "title": "SUBDIVISION",
    "subsections": [{"letter": "a", "title": "PURPOSE"}, ...]}, ...] for
    adopted PDF pages p0..p1 inclusive (0-indexed)."""
    lines: list[str] = []
    for pno in range(p0, p1 + 1):
        for raw in doc[pno].get_text().split("\n"):
            raw = raw.rstrip()
            if raw.strip():
                lines.append(raw)

    nodes: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    seen_letters: set[str] = set()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        m = _SEC_RE.match(line)
        if m:
            num, title = m.group(1), _clean_title(m.group(2))
            if _is_capsy(title) and 1 <= int(num) <= 200:
                cur = {"section": num, "title": title, "subsections": []}
                nodes.append(cur)
                seen_letters = set()
                i += 1
                continue

        mi = _SUB_INLINE_RE.match(line)
        if mi and cur is not None:
            letter, rest = mi.group(1), _clean_title(mi.group(2))
            if _is_capsy(rest) and letter not in seen_letters:
                cur["subsections"].append({"letter": letter, "title": rest})
                seen_letters.add(letter)
                i += 1
                continue

        m2 = _BARE_LETTER_RE.match(line)
        if m2 and cur is not None:
            j = i + 1
            parts: list[str] = []
            while j < n and _is_capsy(lines[j]) and len(parts) < 3:
                parts.append(_clean_title(lines[j]))
                j += 1
            if parts:
                letter = m2.group(1)
                title = _clean_title(" ".join(parts))
                if letter not in seen_letters:
                    cur["subsections"].append({"letter": letter, "title": title})
                    seen_letters.add(letter)
                i = j
                continue

        i += 1

    return nodes


def extract_adopted_nodes(pdf_path: Path = ADOPTED_PDF_PATH) -> dict[int, list[dict[str, Any]]]:
    """Opens the adopted PDF READ-ONLY (never writes to docs/ — CONTRACT.md
    §8.1) and returns {adopted_article_number: [section-node, ...]} for
    every article MATCHED_ADOPTED_ARTICLES names."""
    import fitz  # local import: only the crosswalk builder needs PyMuPDF

    doc = fitz.open(str(pdf_path))
    try:
        ranges = _discover_adopted_article_ranges(doc)
        missing = MATCHED_ADOPTED_ARTICLES - set(ranges)
        if missing:
            raise CrosswalkBuildError(
                f"could not locate page ranges for adopted article(s) {sorted(missing)} in {pdf_path} "
                f"(found ranges for {sorted(ranges)}) — the PDF's layout moved."
            )
        return {art: _extract_adopted_article_nodes(doc, *ranges[art]) for art in sorted(MATCHED_ADOPTED_ARTICLES)}
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# draft markdown section/subsection heading extraction
# --------------------------------------------------------------------------- #

_DRAFT_SEC_RE = re.compile(r"^## (\d{1,3})\. (.+?)\s*$")
_DRAFT_SUB_RE = re.compile(r"^### ([a-z])\. (.+?)\s*$")


def extract_draft_nodes(md_path: Path) -> list[dict[str, Any]]:
    """Returns the same shape as _extract_adopted_article_nodes(), read from
    one source/article-0N-*.md's '## <int>. TITLE' / top-level (unindented)
    '### <letter>. TITLE' headings (CONTRACT.md's documented draft grammar)."""
    nodes: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for line in md_path.read_text(encoding="utf-8").split("\n"):
        m = _DRAFT_SEC_RE.match(line)
        if m:
            cur = {"section": m.group(1), "title": m.group(2).strip(), "subsections": []}
            nodes.append(cur)
            continue
        m2 = _DRAFT_SUB_RE.match(line)
        if m2 and cur is not None:
            cur["subsections"].append({"letter": m2.group(1), "title": m2.group(2).strip()})
    return nodes


# --------------------------------------------------------------------------- #
# matching
# --------------------------------------------------------------------------- #


def _node_id(scheme: str, article: int, section: str, letter: str | None = None) -> str:
    base = f"{scheme}:a{article}.s{section}"
    return f"{base}.{letter}" if letter else base


def _match_article(
    adopted_article: int,
    draft_article: int,
    adopted_nodes: list[dict[str, Any]],
    draft_nodes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (matches, unmatched_adopted, unmatched_draft) for one article
    pair. A match is anchored on section-NUMBER identity — CONTRACT.md §5.3's
    verified fact that section numbers are preserved across schemes — never
    on title similarity alone (that would risk inventing a match)."""
    matches: list[dict[str, Any]] = []
    unmatched_adopted: list[dict[str, Any]] = []
    unmatched_draft: list[dict[str, Any]] = []

    adopted_by_num = {nd["section"]: nd for nd in adopted_nodes}
    draft_by_num = {nd["section"]: nd for nd in draft_nodes}

    for num, a_node in sorted(adopted_by_num.items(), key=lambda kv: int(kv[0])):
        a_id = _node_id("adopted", adopted_article, num)
        d_node = draft_by_num.get(num)
        if d_node is None:
            unmatched_adopted.append(
                {"id": a_id, "article": adopted_article, "section": num, "title": a_node["title"], "level": "section"}
            )
            continue

        d_id = _node_id("draft", draft_article, num)
        sim = _title_similarity(a_node["title"], d_node["title"])
        entry: dict[str, Any] = {
            "adopted_id": a_id,
            "draft_id": d_id,
            "level": "section",
            "adopted_title": a_node["title"],
            "draft_title": d_node["title"],
            "confidence": sim,
            "match_basis": "section_number",
        }
        if sim < 0.5:
            entry["note"] = "titles diverge — verify by hand; the section NUMBER still lines up."
        matches.append(entry)

        # Subsections only within a section-number-matched pair.
        a_subs = {s["letter"]: s for s in a_node["subsections"]}
        d_subs = {s["letter"]: s for s in d_node["subsections"]}
        for letter, a_sub in sorted(a_subs.items()):
            as_id = _node_id("adopted", adopted_article, num, letter)
            d_sub = d_subs.get(letter)
            if d_sub is None:
                unmatched_adopted.append(
                    {
                        "id": as_id,
                        "article": adopted_article,
                        "section": num,
                        "subsection": letter,
                        "title": a_sub["title"],
                        "level": "subsection",
                    }
                )
                continue
            ds_id = _node_id("draft", draft_article, num, letter)
            sub_sim = _title_similarity(a_sub["title"], d_sub["title"])
            sub_entry = {
                "adopted_id": as_id,
                "draft_id": ds_id,
                "level": "subsection",
                "adopted_title": a_sub["title"],
                "draft_title": d_sub["title"],
                "confidence": sub_sim,
                "match_basis": "section_number+subsection_letter",
            }
            if sub_sim < 0.5:
                sub_entry["note"] = "titles diverge — verify by hand; section+letter still line up."
            matches.append(sub_entry)
        for letter, d_sub in sorted(d_subs.items()):
            if letter not in a_subs:
                unmatched_draft.append(
                    {
                        "id": _node_id("draft", draft_article, num, letter),
                        "article": draft_article,
                        "section": num,
                        "subsection": letter,
                        "title": d_sub["title"],
                        "level": "subsection",
                    }
                )

    for num, d_node in sorted(draft_by_num.items(), key=lambda kv: int(kv[0])):
        if num not in adopted_by_num:
            unmatched_draft.append(
                {
                    "id": _node_id("draft", draft_article, num),
                    "article": draft_article,
                    "section": num,
                    "title": d_node["title"],
                    "level": "section",
                }
            )

    return matches, unmatched_adopted, unmatched_draft


def _load_overrides(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_README": _OVERRIDES_README, "entries": {}}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


_OVERRIDES_README = (
    "Hand-curated corrections to rulesets/crosswalk.json's automatic node matching. "
    "ruleset_build/crosswalk.py NEVER invents a match from title similarity alone; every "
    "automatic match is anchored on section-number identity. This file is where a HUMAN "
    "resolves the rest — e.g. a section that was renumbered between the adopted Code and "
    "the draft, so it shows up in both sides' 'unmatched' lists even though it is really "
    "the same provision under a new number. Never machine-generated beyond this seed. "
    "One entry per SOURCE node id (either 'adopted:aX.sY[.letter]' or 'draft:aX.sY[.letter]'). "
    "Schema: {\"<source_id>\": {\"counterpart_id\": \"<other_id>\", \"confidence\": 1.0, "
    "\"basis\": \"<short reason>\", \"decided_by\": \"<name>\", \"decided_at\": \"<ISO date>\", "
    "\"note\": \"<why>\"}}. An entry with a null 'counterpart_id' or 'decided_by' is NOT applied "
    "— same discipline as overrides/dimension-qualifiers.json (CONTRACT.md §4.2.4): a placeholder "
    "is not a resolution."
)


def _apply_overrides(
    matches: list[dict[str, Any]],
    unmatched_adopted: list[dict[str, Any]],
    unmatched_draft: list[dict[str, Any]],
    overrides: dict[str, Any],
) -> None:
    """Mutates the three lists in place: a fully-decided override entry
    (non-null counterpart_id AND decided_by) removes its source id from
    whichever unmatched list holds it (on both sides, since round-tripping
    must find it) and appends a match record. An incomplete entry (any
    required field null) is a placeholder, not a resolution, and changes
    nothing — CONTRACT.md §4.2.4's discipline, mirrored here."""
    entries = overrides.get("entries") or {}
    unmatched_by_id = {
        "adopted": {n["id"]: n for n in unmatched_adopted},
        "draft": {n["id"]: n for n in unmatched_draft},
    }
    for source_id, entry in entries.items():
        counterpart_id = entry.get("counterpart_id")
        if not counterpart_id or not entry.get("decided_by"):
            continue  # placeholder, not a resolution

        source_side = "adopted" if source_id.startswith("adopted:") else "draft"
        target_side = "draft" if source_side == "adopted" else "adopted"
        adopted_id, draft_id = (
            (source_id, counterpart_id) if source_side == "adopted" else (counterpart_id, source_id)
        )

        source_node = unmatched_by_id[source_side].pop(source_id, None)
        target_node = unmatched_by_id[target_side].pop(counterpart_id, None)
        if source_node is None and target_node is None:
            continue  # neither id is currently unmatched -- nothing to resolve

        title_node = source_node or target_node
        matches.append(
            {
                "adopted_id": adopted_id,
                "draft_id": draft_id,
                "level": title_node.get("level", "section") if title_node else "section",
                "adopted_title": (source_node or {}).get("title") if source_side == "adopted" else None,
                "draft_title": (source_node or {}).get("title") if source_side == "draft" else None,
                "confidence": entry.get("confidence", 1.0),
                "match_basis": f"override:{entry.get('basis', 'manual')}",
                "note": entry.get("note"),
            }
        )
        if source_node is not None:
            (unmatched_adopted if source_side == "adopted" else unmatched_draft).remove(source_node)
        if target_node is not None:
            (unmatched_adopted if target_side == "adopted" else unmatched_draft).remove(target_node)


def build_crosswalk(
    *,
    pdf_path: Path = ADOPTED_PDF_PATH,
    source_dir: Path = SOURCE_DIR,
    overrides_path: Path,
) -> dict[str, Any]:
    """Builds the full newcastle.crosswalk/1.0.0 document."""
    draft_names, draft_files = _read_draft_article_names(source_dir)
    adopted_nodes_by_article = extract_adopted_nodes(pdf_path)

    all_matches: list[dict[str, Any]] = []
    all_unmatched_adopted: list[dict[str, Any]] = []
    all_unmatched_draft: list[dict[str, Any]] = []

    for adopted_article in sorted(MATCHED_ADOPTED_ARTICLES):
        draft_article = RENUM_ADOPTED_TO_DRAFT[adopted_article]
        md_path = REPO_ROOT / draft_files[draft_article]
        draft_nodes = extract_draft_nodes(md_path)
        adopted_nodes = adopted_nodes_by_article[adopted_article]

        m, ua, ud = _match_article(adopted_article, draft_article, adopted_nodes, draft_nodes)
        all_matches.extend(m)
        all_unmatched_adopted.extend(ua)
        all_unmatched_draft.extend(ud)

    overrides = _load_overrides(overrides_path)
    _apply_overrides(all_matches, all_unmatched_adopted, all_unmatched_draft, overrides)

    all_matches.sort(key=lambda e: (e["adopted_id"], e["level"]))
    all_unmatched_adopted.sort(key=lambda e: e["id"])
    all_unmatched_draft.sort(key=lambda e: e["id"])

    return {
        "schema": "newcastle.crosswalk/1.0.0",
        "generated_at": _now_iso(),
        "source": {
            "adopted_pdf": "docs/Newcastle Core Zoning Code.pdf",
            "adopted_pdf_sha256": _sha256_file(pdf_path),
            "draft_dir": "source/",
            "overrides_applied": str(overrides_path.relative_to(REPO_ROOT))
            if overrides_path.exists()
            else None,
        },
        "matched_articles": {
            str(a): {"adopted": a, "draft": RENUM_ADOPTED_TO_DRAFT[a]} for a in sorted(MATCHED_ADOPTED_ARTICLES)
        },
        "excluded_articles": EXCLUDED_ARTICLES,
        "counts": {
            "matches": len(all_matches),
            "matches_section_level": sum(1 for m in all_matches if m["level"] == "section"),
            "matches_subsection_level": sum(1 for m in all_matches if m["level"] == "subsection"),
            "unmatched_adopted": len(all_unmatched_adopted),
            "unmatched_draft": len(all_unmatched_draft),
        },
        "matches": all_matches,
        "unmatched": {"adopted": all_unmatched_adopted, "draft": all_unmatched_draft},
    }


def counterpart(node_id: str, crosswalk: dict[str, Any]) -> str | None:
    """Looks up node_id's counterpart in a crosswalk.json document, in
    either direction. Returns None if node_id is not in any match (it may
    legitimately be unmatched, or simply not exist)."""
    for m in crosswalk.get("matches", []):
        if m.get("adopted_id") == node_id:
            return m.get("draft_id")
        if m.get("draft_id") == node_id:
            return m.get("adopted_id")
    return None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=APP_ROOT / "rulesets")
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    article_map_path = out_dir / "article-map.json"
    crosswalk_path = out_dir / "crosswalk.json"
    overrides_path = out_dir / "crosswalk-overrides.json"

    article_map = build_article_map()
    _atomic_write_json(article_map_path, article_map)
    print(f"wrote {article_map_path.relative_to(APP_ROOT)}")

    if not overrides_path.exists():
        _atomic_write_json(overrides_path, {"_README": _OVERRIDES_README, "entries": {}})
        print(f"wrote {overrides_path.relative_to(APP_ROOT)} (seeded empty)")

    crosswalk = build_crosswalk(overrides_path=overrides_path)
    _atomic_write_json(crosswalk_path, crosswalk)
    counts = crosswalk["counts"]
    print(
        f"wrote {crosswalk_path.relative_to(APP_ROOT)}  "
        f"matches={counts['matches']} (section={counts['matches_section_level']}, "
        f"subsection={counts['matches_subsection_level']})  "
        f"unmatched_adopted={counts['unmatched_adopted']}  unmatched_draft={counts['unmatched_draft']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
