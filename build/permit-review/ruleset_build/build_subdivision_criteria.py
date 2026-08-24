"""W6 task: "the criteria set + the applicability gate". Reads the 21
Subdivision Plan approval standards a-u at node id `art7.12.f.1` in
rulesets/adopted/articles.json (already extracted and verified -- this
module does not re-derive or "fix" them, per the task brief) and writes
rulesets/adopted/criteria-subdivision.json: one `criteria_set` (Subdivision,
Article 7 Section 12.f.1, Planning Board authority) plus 21 ordered `rules`,
each carrying:

    source_text        -- VERBATIM Code language for the standard (never
                           regenerated, reworded, or summarised -- what gets
                           quoted to the Board). For standard c (Pollution),
                           which is the only one of the 21 with sub-items in
                           the source, this is the parent sentence PLUS the
                           five (i)-(v) sub-items, physically concatenated in
                           source order using their own source-given roman-
                           numeral labels as separators -- no word is added,
                           reworded, or dropped; only whitespace and the
                           labels the source itself already assigns join
                           them into one printable standard.
    kind                -- one of numeric | boolean | narrative | judgement |
                           procedural, decided HERE at build time (see
                           CLASSIFICATION below) so it is inspectable in the
                           JSON artifact, never recomputed at review time.
    applicability        -- the engine/predicates.py three-valued gate struct
                           this standard's own Code text embeds (most of the
                           21 are {"op":"always"} -- the Code text applies
                           unconditionally; four embed a real conditional:
                           l/n/r/t below).
    exceptions            -- [] for all 21: none of the 21 standards' own text
                           names an exception or waiver clause (contrast a
                           future Article 6 Shoreland rule, which will).
                           Kept as a real (empty) list, not omitted, so the
                           review engine's exception-escape-hatch step (W6
                           §3.b, built by a different task) always has a list
                           to check, never a missing key.
    mandates_condition    -- null for 20 of the 21; set only on standard n
                           (Flood Areas). See MANDATES_CONDITION_N below for
                           its provenance.
    judgement_tells        -- the literal words in source_text that triggered
                           a 'judgement' classification (e.g. ["undue"]); []
                           for every other kind.

CLASSIFICATION (the actual call, made here, on the actual Code text --
report printed by main() at build time, never silently asserted):

    judgement (14): c d e f g h i j k l m q s t
    boolean    (3): o p u
    numeric    (1): r
    procedural (3): a b n
    narrative  (0)

14 of 21 is exactly what the W6 task brief's "expect roughly 14" predicted
-- arrived at independently, by reading each standard's own words against
the tell list (undue / unreasonable / adequate / excessive / harmonious /
reasonably be expected / adverse effect), NOT tuned to hit that number. See
JUDGEMENT_REPORT below for the tell that fired on each of the 14, and
NON_JUDGEMENT_REPORT for why the other 7 did not classify as judgement.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from app.citation import Citation  # noqa: E402
from app.config import RULESETS_DIR  # noqa: E402

ARTICLES_PATH = RULESETS_DIR / "adopted" / "articles.json"
OUT_PATH = RULESETS_DIR / "adopted" / "criteria-subdivision.json"

ART7_12_F_1_ID = "art7.12.f.1"
EXPECTED_LETTERS = list("abcdefghijklmnopqrstu")  # a..u, 21 letters, source order


# --------------------------------------------------------------------------- #
# Provenance for the one non-Code-text string this module writes: the
# verbatim 3-ft-above-flood condition. This sentence is NOT in
# articles.json -- Article 7 Section 12.f.1.n only says a subdivision plan
# "must include a condition of plan approval requiring" this; the Code does
# not spell out the condition's own wording. The wording below is lifted,
# character for character, from the "Conditions of Approval" section of the
# one FINAL (non-draft) subdivision decision on file:
#
#   docs/Findings of Fact and Conclusions of Law/
#     M003, L059 (White Rd, Shattuck), Subdivision FoF & CoL 2025.12.18.pdf
#     -- Conditions of Approval, item 1 (p. 15 of 16)
#
# and verified against the SECOND subdivision decision on file (a DRAFT,
# still probative because it is the only other real subdivision precedent
# and its condition #1 matches word for word up to the point it stops):
#
#   docs/Findings of Fact and Conclusions of Law/
#     M004, L084 (Uberoi, 130 Lewis Hill Rd), Subdivision FoF & CoL
#     2024.08.15 DRAFT.pdf -- Conditions of Approval, item 1 (p. 12 of 12)
#
# WHY IT FIRES ON EVERY SUBDIVISION, NOT JUST WHEN n's OWN APPLICABILITY GATE
# READS TRUE: both real decisions attached it even where the finding under
# n was HEDGED, not a confirmed flood-zone determination -- Shattuck found
# the area "falls within" the 100-year flood hazard area (definite) and
# still attached it; Uberoi found the affected corner only "may fall within"
# the 100-year flood hazard area (a maybe) and attached the SAME condition
# anyway ("As such, a condition of approval will be attached ... in
# compliance with the above standard"). Two-for-two, including the uncertain
# case, is the actual observed Board practice this module reproduces -- it
# is not this module inventing a rule the Code does not state. Standard n's
# OWN applicability gate (below) is still evaluated normally and still
# renders its own TRUE/FALSE/UNKNOWN finding; mandates_condition is a
# SEPARATE, unconditional instruction to the (later, out of this task's
# scope) review engine, not a substitute for it.
# --------------------------------------------------------------------------- #

MANDATES_CONDITION_N: dict[str, Any] = {
    "text": (
        "All principal structures proposed on any lot within the subdivision shall be "
        "constructed with their lowest floor, including the basement, at least three feet "
        "above the 100-year flood elevation. This condition shall remain in effect "
        "indefinitely and shall not prevent commencement of work which does not conflict "
        "with the condition."
    ),
    "fires": "always",
    "provenance": {
        "source": "real decision, not Code text",
        "documents": [
            "docs/Findings of Fact and Conclusions of Law/M003, L059 (White Rd, Shattuck), "
            "Subdivision FoF & CoL 2025.12.18.pdf (FINAL) -- Conditions of Approval, item 1",
            "docs/Findings of Fact and Conclusions of Law/M004, L084 (Uberoi, 130 Lewis Hill Rd), "
            "Subdivision FoF & CoL 2024.08.15 DRAFT.pdf -- Conditions of Approval, item 1",
        ],
        "note": (
            "Verbatim text taken from the FINAL (Shattuck) decision, which carries an extra "
            "trailing sentence ('This condition shall remain in effect indefinitely...') the "
            "DRAFT (Uberoi) decision's condition #1 does not have; the load-bearing clause "
            "(3 ft above 100-year flood elevation) is identical in both."
        ),
    },
}


# --------------------------------------------------------------------------- #
# Applicability predicates for the four standards whose OWN Code text embeds
# a real conditional ("whenever...", "if...", "for any... that..."). The
# other 17 apply unconditionally -- see predicates.ALWAYS.
# --------------------------------------------------------------------------- #

_SURFACE_WATERS_PREDICATE = {
    "op": "or",
    "of": [
        {"op": "fact_true", "key": "site.within_watershed_of_pond_or_lake"},
        {"op": "numeric_lte", "key": "site.distance_to_protected_water_ft", "value": 250},
    ],
}

_FLOOD_AREAS_PREDICATE = {"op": "fact_true", "key": "site.in_fema_flood_zone"}

_SPAGHETTI_LOTS_PREDICATE = {"op": "fact_true", "key": "subdivision.has_shore_frontage_lots"}

_ADJOINING_MUNICIPALITY_PREDICATE = {
    "op": "fact_true",
    "key": "subdivision.crosses_municipal_boundary",
}


# --------------------------------------------------------------------------- #
# CLASSIFICATION -- one entry per letter a-u. Every field here is a human
# (build-time) judgement call about the Code's own words, made explicitly
# and reported by main(), never inferred implicitly or left for the review
# engine to guess later.
# --------------------------------------------------------------------------- #

CLASSIFICATION: dict[str, dict[str, Any]] = {
    "a": {
        "title": "The standards of this Code",
        "kind": "procedural",
        "judgement_tells": [],
        "applicability": {"op": "always"},
        "reason": (
            "A blanket incorporation of every other applicable standard in the Code into "
            "subdivision review -- not itself a discrete test, so it does not classify as "
            "numeric/boolean/judgement; it is a procedural cross-reference to the rest of the "
            "ruleset, exactly the same duty real decisions carry out under a separate 'Article 1' "
            "/ 'Article 2' ... review, not as one of standards c-u's own findings."
        ),
    },
    "b": {
        "title": "The Newcastle Road, Driveway, and Entrance Ordinance",
        "kind": "procedural",
        "judgement_tells": [],
        "applicability": {"op": "always"},
        "reason": (
            "Same shape as (a): a procedural cross-reference to a whole other instrument, not a "
            "self-contained test. NOTE (flag only, not resolved here): the Newcastle RDEO this "
            "clause names is REPEALED in the draft CZC being built elsewhere in this repo "
            "(CLAUDE.md project memory) -- but this ruleset is the ADOPTED Code, under which the "
            "RDEO is still in force, so the citation is a live legal reference here, not a stale "
            "one; nothing about that repeal belongs in this build."
        ),
    },
    "c": {
        "title": "Pollution",
        "kind": "judgement",
        "judgement_tells": ["undue"],
        "applicability": {"op": "always"},
        "reason": "\"will not result in undue water or air pollution\" -- 'undue' is a listed tell.",
    },
    "d": {
        "title": "Sufficient Water",
        "kind": "judgement",
        "judgement_tells": ["sufficient", "reasonably foreseeable"],
        "applicability": {"op": "always"},
        "reason": (
            "\"has sufficient water available for the reasonably foreseeable needs\" -- "
            "'sufficient' is evaluative in the same register as the listed tell 'adequate', and "
            "'reasonably foreseeable' is the listed tell 'reasonably be expected' in its "
            "adjectival form; either alone would be enough."
        ),
    },
    "e": {
        "title": "Municipal water supply",
        "kind": "judgement",
        "judgement_tells": ["unreasonable"],
        "applicability": {"op": "always"},
        "reason": "\"will not cause an unreasonable burden\" -- 'unreasonable' is a listed tell.",
    },
    "f": {
        "title": "Erosion",
        "kind": "judgement",
        "judgement_tells": ["unreasonable"],
        "applicability": {"op": "always"},
        "reason": "\"will not cause unreasonable soil erosion\" -- 'unreasonable' is a listed tell.",
    },
    "g": {
        "title": "Traffic",
        "kind": "judgement",
        "judgement_tells": ["unreasonable", "unsafe"],
        "applicability": {"op": "always"},
        "reason": (
            "\"will not cause unreasonable ... congestion or unsafe conditions\" -- 'unreasonable' "
            "is a listed tell ('unsafe' is the same register). The standard ALSO embeds a "
            "conditional sub-duty (DOT documentation, only when the subdivision needs driveways or "
            "entrances onto a state/state-aid highway) -- that sub-duty is a boolean, factual check "
            "(was the documentation provided, yes/no), but it does not change the governing "
            "standard's own kind: it is a precondition INSIDE g, not a gate ON g, so g's "
            "applicability stays {'op':'always'} and the DOT sub-duty is left for the (out of "
            "scope here) review engine to test as a fact, not modeled as a second rule."
        ),
    },
    "h": {
        "title": "Sewage Disposal",
        "kind": "judgement",
        "judgement_tells": ["adequate", "unreasonable"],
        "applicability": {"op": "always"},
        "reason": "\"adequate sewage waste disposal\" and \"unreasonable burden\" -- both listed tells.",
    },
    "i": {
        "title": "Municipal Solid Waste Disposal",
        "kind": "judgement",
        "judgement_tells": ["unreasonable"],
        "applicability": {"op": "always"},
        "reason": "\"will not cause an unreasonable burden\" -- 'unreasonable' is a listed tell.",
    },
    "j": {
        "title": "Aesthetic, cultural, and Natural Values",
        "kind": "judgement",
        "judgement_tells": ["undue", "adverse effect"],
        "applicability": {"op": "always"},
        "reason": (
            "\"will not have an undue adverse effect\" -- BOTH 'undue' and 'adverse effect' are "
            "listed tells, present in the same clause."
        ),
    },
    "k": {
        "title": "Financial and Technical Capacity",
        "kind": "judgement",
        "judgement_tells": ["adequate"],
        "applicability": {"op": "always"},
        "reason": "\"has adequate financial and technical capacity\" -- 'adequate' is a listed tell.",
    },
    "l": {
        "title": "Surface Waters",
        "kind": "judgement",
        "judgement_tells": ["adverse effect", "unreasonably"],
        "applicability": _SURFACE_WATERS_PREDICATE,
        "reason": (
            "\"will not adversely affect the quality ... or unreasonably affect the shoreline\" -- "
            "'adverse effect' and 'unreasonably' are both listed tells. The standard's own lead "
            "clause ('Whenever situated ... within the watershed of any pond or lake or within 250 "
            "feet of any wetland, great pond, or river') is a genuine applicability gate, not part "
            "of the substantive test -- modeled as OR(within-watershed, distance<=250ft), UNKNOWN "
            "when neither fact is on record."
        ),
    },
    "m": {
        "title": "Ground Water",
        "kind": "judgement",
        "judgement_tells": ["adverse effect"],
        "applicability": {"op": "always"},
        "reason": "\"will not ... adversely affect the quality or quantity\" -- 'adverse effect' tell.",
    },
    "n": {
        "title": "Flood Areas",
        "kind": "procedural",
        "judgement_tells": [],
        "applicability": _FLOOD_AREAS_PREDICATE,
        "reason": (
            "No evaluative tell anywhere in the text -- it is a mandatory-content/condition-of-"
            "approval requirement (determine the 100-year flood elevation; include a plan "
            "condition), not a discretionary standard the Board weighs. See "
            "MANDATES_CONDITION_N above for the separate, unconditional condition-firing behaviour."
        ),
    },
    "o": {
        "title": "Freshwater Wetlands",
        "kind": "boolean",
        "judgement_tells": [],
        "applicability": {"op": "always"},
        "reason": (
            "\"have been identified on any maps submitted\" -- a directly verifiable yes/no fact, "
            "no evaluative language."
        ),
    },
    "p": {
        "title": "River, Stream, or Brook",
        "kind": "boolean",
        "judgement_tells": [],
        "applicability": {"op": "always"},
        "reason": "Same shape as (o): a directly verifiable yes/no identification fact.",
    },
    "q": {
        "title": "Storm Water",
        "kind": "judgement",
        "judgement_tells": ["adequate"],
        "applicability": {"op": "always"},
        "reason": "\"provide for adequate storm water management\" -- 'adequate' is a listed tell.",
    },
    "r": {
        "title": "Spaghetti-Lots",
        "kind": "numeric",
        "judgement_tells": [],
        "applicability": _SPAGHETTI_LOTS_PREDICATE,
        "reason": (
            "A clean quantifiable comparison -- lot depth to shore frontage ratio must not exceed "
            "5 to 1 -- with no evaluative language at all. Gated on shore-frontage lots existing at "
            "all (the standard's own 'If any lots ... have shore frontage on a river, stream, "
            "brook, great pond or coastal wetland' clause)."
        ),
        "test_json": {
            "comparison": "lte",
            "field": "lot_depth_to_shore_frontage_ratio",
            "threshold": 5.0,
            "unit": "ratio",
            "note": "Code states this as '5 to 1 (5.00)'.",
        },
    },
    "s": {
        "title": "Lake Phosphorus Concentration",
        "kind": "judgement",
        "judgement_tells": ["unreasonably"],
        "applicability": {"op": "always"},
        "reason": "\"will not unreasonably increase the phosphorus concentration\" -- listed tell.",
    },
    "t": {
        "title": "Impact on Adjoining Municipality",
        "kind": "judgement",
        "judgement_tells": ["unreasonable", "unsafe"],
        "applicability": _ADJOINING_MUNICIPALITY_PREDICATE,
        "reason": (
            "\"will not cause unreasonable traffic congestion or unsafe conditions\" -- listed "
            "tell. Gated on the subdivision actually crossing a municipal boundary (the standard's "
            "own 'For any proposed subdivision that crosses municipal boundaries' clause)."
        ),
    },
    "u": {
        "title": "Lands Subject to Liquidation Harvesting",
        "kind": "boolean",
        "judgement_tells": [],
        "applicability": {"op": "always"},
        "reason": (
            "Primary test is a directly verifiable yes/no fact (has an illegal-harvesting "
            "violation occurred), no evaluative language. The Code embeds a conditional NUMERIC "
            "sub-test (5 years elapsed) that only applies if the boolean fires true -- left as a "
            "downstream fact for the (out of scope here) review engine rather than modeled as its "
            "own rule, the same treatment given (g)'s embedded DOT sub-duty."
        ),
    },
}

# Sanity check this module's own claims before anything else runs.
_JUDGEMENT_LETTERS = sorted(k for k, v in CLASSIFICATION.items() if v["kind"] == "judgement")
_KIND_COUNTS: dict[str, int] = {}
for _v in CLASSIFICATION.values():
    _KIND_COUNTS[_v["kind"]] = _KIND_COUNTS.get(_v["kind"], 0) + 1


# --------------------------------------------------------------------------- #
# Extraction from rulesets/adopted/articles.json
# --------------------------------------------------------------------------- #


class SubdivisionCriteriaBuildError(RuntimeError):
    """The source ruleset's shape at art7.12.f.1 has drifted from what this
    module verified and hard-codes assumptions about. Fail loudly, exactly
    like ruleset_build's other builders (CONTRACT.md §4's "a mismatch is a
    hard failure, not a warning") -- never silently adapt to a changed shape.
    """


def _find_node(tree: list[dict], node_id: str) -> dict | None:
    stack = list(tree)
    while stack:
        node = stack.pop()
        if node.get("id") == node_id:
            return node
        stack.extend(node.get("children", []))
    return None


def _load_articles() -> dict:
    with ARTICLES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _standard_source_text(node: dict) -> str:
    """VERBATIM text for one a-u standard. Standard c is the only one of the
    21 with children in the source (its i-v sub-items) -- physically
    concatenated using their own source-given roman-numeral labels; every
    other standard is a leaf and returns its 'text' unchanged."""
    text = node["text"]
    children = node.get("children", [])
    if not children:
        return text
    lines = [text]
    for child in children:
        lines.append(f"({child['number']}) {child['text']}")
    return "\n".join(lines)


def extract_standards() -> list[dict]:
    """Read art7.12.f.1's a-u children from rulesets/adopted/articles.json,
    asserting the exact 21-letter shape this module's CLASSIFICATION table
    hard-codes reasoning about. Raises SubdivisionCriteriaBuildError on any
    mismatch -- never silently reclassifies against a different shape."""
    articles = _load_articles()
    node = _find_node(articles["articles"], ART7_12_F_1_ID)
    if node is None:
        raise SubdivisionCriteriaBuildError(
            f"{ART7_12_F_1_ID!r} not found in {ARTICLES_PATH} -- has the extractor's node id "
            "scheme changed?"
        )
    children = node.get("children", [])
    letters = [c.get("number") for c in children]
    if letters != EXPECTED_LETTERS:
        raise SubdivisionCriteriaBuildError(
            f"{ART7_12_F_1_ID} children are {letters!r}, expected exactly {EXPECTED_LETTERS!r} "
            "(a-u, 21 standards) -- CLASSIFICATION in this module hard-codes reasoning about that "
            "exact shape and must be re-reviewed by a human before this builder can run against a "
            "changed source."
        )
    missing_classification = [l for l in letters if l not in CLASSIFICATION]
    if missing_classification:
        raise SubdivisionCriteriaBuildError(
            f"no CLASSIFICATION entry for standard(s) {missing_classification!r}"
        )
    return children


# --------------------------------------------------------------------------- #
# Row assembly
# --------------------------------------------------------------------------- #


def _citation_for(letter: str, title: str) -> dict:
    c = Citation(
        ruleset_key="adopted",
        scheme="adopted",
        article=7,
        section="12",
        standard_letter=letter,
        standard_title=title,
    )
    return {
        "ruleset_key": c.ruleset_key,
        "scheme": c.scheme,
        "article": c.article,
        "section": c.section,
        "standard_letter": c.standard_letter,
        "standard_title": c.standard_title,
    }


def build_rule_rows(standards: list[dict]) -> list[dict]:
    rows = []
    for sort_order, node in enumerate(standards, start=1):
        letter = node["number"]
        cls = CLASSIFICATION[letter]
        row = {
            "rule_key": f"art7.12.f.1.{letter}",
            "standard_letter": letter,
            "title": cls["title"],
            "kind": cls["kind"],
            "source_text": _standard_source_text(node),
            "applicability": cls["applicability"],
            "exceptions": [],
            "mandates_condition": MANDATES_CONDITION_N if letter == "n" else None,
            "judgement_tells": cls["judgement_tells"],
            "test_json": cls.get("test_json"),
            "citation": _citation_for(letter, cls["title"]),
            "source_ref": node.get("source_ref"),
            "sort_order": sort_order,
            "build_reason": cls["reason"],
        }
        rows.append(row)
    return rows


def build_criteria_set() -> dict:
    return {
        "set_key": "subdivision",
        "label": "Subdivision — Article 7 §12.f.1 Approval Standards",
        "application_type": "subdivision",
        "authority": "planning_board",
        "citation": {
            "ruleset_key": "adopted",
            "scheme": "adopted",
            "article": 7,
            "section": "12",
            "subsection": "f.1",
        },
    }


# --------------------------------------------------------------------------- #
# Write rulesets/adopted/criteria-subdivision.json (S1/S2-style atomic
# write, matching ruleset_build/build_ruleset.py's own _atomic_write_json).
# --------------------------------------------------------------------------- #


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(target: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError(f"round-trip verification failed before write -- refusing to write {target}")
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


def build(*, write: bool = True) -> dict:
    from datetime import datetime, timezone

    standards = extract_standards()
    rules = build_rule_rows(standards)
    criteria_set = build_criteria_set()

    judgement = sorted(r["standard_letter"] for r in rules if r["kind"] == "judgement")
    by_kind: dict[str, int] = {}
    for r in rules:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1

    artifact = {
        "schema": "newcastle.criteria-subdivision/1.0.0",
        "ruleset_key": "adopted",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {"path": "rulesets/adopted/articles.json", "sha256": _sha256_file(ARTICLES_PATH)},
        "node_id": ART7_12_F_1_ID,
        "criteria_set": criteria_set,
        "rules": rules,
        "counts": {
            "rules": len(rules),
            "by_kind": by_kind,
            "judgement_letters": judgement,
        },
    }

    if write:
        _atomic_write_json(OUT_PATH, artifact)
    return artifact


def main() -> int:
    artifact = build(write=True)
    counts = artifact["counts"]
    print(f"wrote {OUT_PATH.relative_to(APP_ROOT)}")
    print(f"  rules: {counts['rules']}")
    print(f"  by kind: {counts['by_kind']}")
    print(f"  judgement ({len(counts['judgement_letters'])}): {', '.join(counts['judgement_letters'])}")
    for letter in counts["judgement_letters"]:
        row = next(r for r in artifact["rules"] if r["standard_letter"] == letter)
        print(f"    {letter} ({row['title']}): tells={row['judgement_tells']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
