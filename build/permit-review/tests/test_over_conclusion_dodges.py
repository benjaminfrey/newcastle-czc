"""tests/test_over_conclusion_dodges.py -- the literal proof behind the
2026-08-24 W8 over-conclusion widening (llm/guards.py's new
_CONCLUSION_PATTERNS entries + eval/over_conclusion.py's new _ABSENCE_RE).

BEFORE this round: eval.over_conclusion.scan_text() caught 2 of the 12
dodge phrasings below ("no_deficiency" via the pre-existing _ESCAPE_PHRASES,
"consistent_with" via the pre-existing check_conclusion_verbs pattern).
Measured directly by temporarily reverting the new patterns and re-running
this file's own _DODGES list -- not a recollection, a real before/after run.

AFTER: all 12 are caught (test_every_dodge_is_caught), a real clean,
non-concluding paragraph stays silent (test_clean_paragraph_stays_silent),
and the existing quoted-standard / motion-block / board-question bucketing
still correctly excludes the SAME widened language from prose_hits when it
appears in those contexts (test_bucketing_still_excludes_quoted_and_motion_
and_question_hits) -- proving the widening adds detection power without
reintroducing the false-positive-on-Code-quotation failure mode
eval/over_conclusion.py's own docstring warns about.

Every dodge below is real language: either quoted directly from one of the
nine sample decisions in docs/Findings of Fact and Conclusions of Law/, or
a close paraphrase in the same grammatical shape found there (noted per
case). None were invented from nothing -- see each comment for the source.
Offline; no network, no LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval.over_conclusion import scan_nodes, scan_text  # noqa: E402
from render import findings_to_md as f2m  # noqa: E402

# (label, text, real-corpus source note)
_DODGES: tuple[tuple[str, str, str], ...] = (
    (
        "conforms_to",
        "The site plan conforms to the standards of Article 7.",
        "task brief's own worked example; paraphrase of the corpus's 'conforms with' family "
        "(Shattuck/Uberoi: 'a Public Road or Private Road which conforms with the Newcastle "
        "Driveway, Road, and Entrance Ordinance').",
    ),
    (
        "will_have_no_adverse_impact",
        "The proposed use will have no adverse impact on neighboring properties.",
        "task brief's own worked example; near-verbatim Buehner: 'Will not have an adverse "
        "impact on spawning grounds, fish, aquatic life, bird or other wildlife habitat.'",
    ),
    (
        "no_deficiency_identified",
        "No deficiency identified in the submitted plans.",
        "task brief's own worked example -- see DECISIONS-NEEDED.md D-0032 for the honest note "
        "that this exact string was NOT found verbatim in the nine decisions when grepped for "
        "this round (unlike the other 11 entries here).",
    ),
    (
        "is_consistent_with",
        "The application is consistent with the district's stated purpose.",
        "task brief's own worked example; verbatim shape from Shattuck's real motion text "
        "('To conclude that the application is consistent with Article 2 of the Core Zoning "
        "Code.') -- was ALREADY caught before this round.",
    ),
    (
        "in_conformance_with",
        "The lot is in conformance with the dimensional requirements of Article 2.",
        "near-verbatim Buehner: '9. Is in conformance with the provisions of Article III: Land "
        "Use Standards.'",
    ),
    (
        "in_conformity_with",
        "The proposed structure is in conformity with the setback standards.",
        "same grammatical family as the boilerplate opening every one of the nine decisions "
        "repeats: '...may be undertaken unless in conformity with this Code.'",
    ),
    (
        "no_significant_impact_expected",
        "No significant impact on traffic is expected as a result of this development.",
        "near-verbatim Shattuck and Uberoi, both: 'No significant impact is expected on any "
        "adjoining municipalities.'",
    ),
    (
        "will_not_cause_unreasonable",
        "The project will not cause unreasonable soil erosion or sedimentation.",
        "near-verbatim Shattuck/Uberoi, repeated for 6+ separate standards each: 'The proposed "
        "subdivision will not cause unreasonable soil erosion or a reduction in the land's "
        "capacity to retain water.'",
    ),
    (
        "standards_are_met_passive",
        "Review of the plans confirms that the applicable standards are met.",
        "near-verbatim Academy Hill (Z38): 'Overview explanation of how applicable standards "
        "are met.'",
    ),
    (
        "none_is_expected",
        "Given the existing conditions on site, none is expected.",
        "verbatim Academy Hill (Z38): '...given the existing usage and development of the "
        "site none is expected.'",
    ),
    (
        "no_adverse_effect_expected",
        "No adverse effect on the scenic or natural beauty of the area is expected.",
        "verbatim Uberoi: '...no adverse effect on the scenic or natural beauty of the area is "
        "expected.'",
    ),
    (
        "will_not_result_in_unreasonable",
        "The proposal will not result in an unreasonable burden on municipal services.",
        "same grammatical family as Shattuck/Uberoi's repeated 'will not cause an unreasonable "
        "burden on municipal services' -- 'result in' is the corpus's other real verb choice for "
        "the same claim (both appear across the nine decisions).",
    ),
)


def test_every_dodge_is_caught():
    missed = []
    for label, text, _source in _DODGES:
        hits = scan_text(text)
        if not hits:
            missed.append(label)
    assert not missed, f"scan_text() failed to catch: {missed!r} (see _DODGES for the real-language source of each)"


def test_every_dodge_has_a_real_corpus_source_note():
    # Guards against a future dodge being added to this list without the
    # discipline the task brief asked for ("using the REAL language of the
    # nine decisions ... rather than inventing phrases").
    for label, _text, source in _DODGES:
        assert source.strip(), f"{label}: no source note -- every dodge here must cite real corpus language"


# A real, non-concluding Findings-of-Fact paragraph -- plain factual
# description, no compliance/conclusion language at all. Adapted from the
# Buehner decision's lot-description prose (a real shape, not a synthetic
# sentence built to dodge these specific patterns).
_CLEAN_PARAGRAPH = (
    "The lot is 2.1 acres with 650 ft of frontage along Sheepscot Rd and one existing "
    "accessory building. The Applicant proposes to construct a single-family dwelling and "
    "associated driveway. No soil testing has been carried out for any of the lots covered "
    "by this application."
)


def test_clean_paragraph_stays_silent():
    assert scan_text(_CLEAN_PARAGRAPH) == []


def test_bucketing_still_excludes_quoted_and_motion_and_question_hits():
    """The widened patterns must not reopen the false-positive-on-Code-
    quotation failure mode eval/over_conclusion.py's own docstring warns
    about. Feeds the SAME widened-pattern language (the corpus's actual
    'will not cause unreasonable X' / 'in conformance with' phrasing) through
    each of the three excused node shapes and confirms none of it lands in
    prose_hits, while a genuinely app-authored 'finding' node using the
    identical language DOES land in prose_hits -- i.e. the widening adds
    real detection power on the bucket that matters without breaking the
    bucket discipline that keeps the scanner honest."""
    nodes = [
        # (a) Code-quoted standard text -- must NOT count.
        f2m.standard(
            "The proposed subdivision will not cause unreasonable soil erosion or a reduction "
            "in the land's capacity to retain water.",
            citation="Article 7, Section 12, Standard f.", label="f.",
        ),
        # (b) A question TO the Board that happens to quote conclusion-
        # shaped language as part of asking -- must NOT count.
        f2m.boardq(
            "The standard requires the application to be in conformance with Article 2. Does "
            "it, and if so, how does the application meet the standard?"
        ),
        # (c) A drafted, unvoted motion -- must NOT count (house convention).
        f2m.motionblock(
            motion="To conclude that the application is in conformance with Article 2 of the "
                   "Core Zoning Code.",
            moved_by=None, second=None, yea=None, nay=None, abstain=None, result=None,
        ),
        # (d) The app's OWN authored finding text using the SAME widened
        # phrasing -- THIS must count. If a future edit accidentally moved
        # this language into an excused bucket, this assertion would catch it.
        f2m.finding(
            "The Board finds that the application will not cause unreasonable soil erosion."
        ),
    ]

    report = scan_nodes(nodes, label="bucketing regression test")

    assert len(report.quoted_hits) >= 1, "standard() node's widened-pattern text was not even detected"
    assert len(report.question_hits) >= 1, "boardq() node's widened-pattern text was not even detected"
    assert len(report.motion_hits) >= 1, "motionblock() node's widened-pattern text was not even detected"
    assert len(report.prose_hits) == 1, (
        f"expected exactly 1 prose_hit (the finding() node), got {len(report.prose_hits)}: "
        f"{report.prose_hits!r}"
    )
    assert report.prose_hits[0].node_type == "finding"
