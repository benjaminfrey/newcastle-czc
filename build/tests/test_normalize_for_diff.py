# build/tests/test_normalize_for_diff.py
"""Normalisation rules for the baseline redline.

Each rule gets TWO tests: it suppresses the cosmetic difference, AND a real
change of the same shape still survives. The second test is the point. A
normaliser that quietly eats a real amendment produces a redline that is
confidently wrong, and nobody reading it can tell.
"""
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

AMAP = adoption_map.load(Path(__file__).resolve().parent / "fixtures" / "adoption-map-v0.1-baseline.json")


import pytest as _pytest_rollover

_PRE_ROLLOVER_MAP = Path(__file__).resolve().parent / "fixtures" / "adoption-map-v0.1-baseline.json"


@_pytest_rollover.fixture(autouse=True)
def _pin_pre_rollover_adoption_map(monkeypatch):
    """These tests exercise the baseline-redline machinery -- renumbering,
    renamed article files, not-text-comparable articles -- against the
    v0.1-baseline map it was built for. The shipped map was rolled over to
    identity at the v1.0 adoption (September 14, 2026) and no longer exercises
    any of that, so the pre-rollover map is pinned here as a fixture."""
    monkeypatch.setenv("ADOPTION_MAP", str(_PRE_ROLLOVER_MAP))


def norm_old(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=True)


def norm_new(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=False)


# --- Rule 1: heading letter case -------------------------------------------

def test_heading_case_difference_is_suppressed():
    assert norm_old("### A. PURPOSE") == norm_new("### a. PURPOSE")


def test_but_a_changed_heading_WORD_still_differs():
    assert norm_old("### A. PURPOSE") != norm_new("### a. APPLICABILITY")


def test_case_normalisation_does_not_touch_body_text():
    """Only the heading's leading letter is lowered. Body prose keeps its case,
    including defined terms like Driveway and Thoroughfare."""
    body = "1. A Driveway serves no more than two Dwellings."
    assert norm_new(body) == body


# --- Rule 2: cross-reference renumbering ------------------------------------

def test_renumbering_is_suppressed_on_the_baseline_side_only():
    assert norm_old("See Article 7.") == norm_new("See Article 8.")


def test_but_a_reference_to_a_genuinely_different_article_still_differs():
    assert norm_old("See Article 7.") != norm_new("See Article 5.")


def test_the_new_side_is_never_renumbered():
    """Renumbering maps baseline->current. Applying it to the current side too
    would double-shift and silently corrupt every reference."""
    assert norm_new("See Article 7.") == "See Article 7."


# --- Rule 4: table-number renumbering ---------------------------------------

def test_table_number_renumbering_is_suppressed_all_caps():
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") == \
        norm_new("TABLE 7.1 DESIGN STANDARDS BY DISTRICT")


def test_table_number_renumbering_is_suppressed_title_case():
    assert norm_old("See Table 4.2 Site Lumens.") == norm_new("See Table 5.2 Site Lumens.")


def test_table_number_renumbering_is_suppressed_lowercase():
    """The real case found in the corpus: article-06-design-standards.md's
    baseline reads 'table 5.1 Design Standards By District' (lowercase)."""
    assert norm_old("designated in table 5.1 Design Standards By District.") == \
        norm_new("designated in table 6.1 Design Standards By District.")


def test_but_a_table_renumbered_for_a_different_reason_still_differs():
    """The article shift predicts TABLE 6.1 -> TABLE 7.1. A table actually
    renumbered to something else (inserted/reordered table) must still show."""
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") != \
        norm_new("TABLE 7.3 DESIGN STANDARDS BY DISTRICT")


def test_but_a_renamed_table_title_still_differs():
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") != \
        norm_new("TABLE 7.1 DIMENSIONAL STANDARDS BY DISTRICT")


def test_the_new_side_table_numbers_are_never_renumbered():
    assert norm_new("TABLE 7.1 DESIGN STANDARDS BY DISTRICT") == \
        "TABLE 7.1 DESIGN STANDARDS BY DISTRICT"


def test_normalize_old_side_also_renumbers_tables():
    assert nz.normalize_old_side("TABLE 6.1 DESIGN STANDARDS BY DISTRICT", amap=AMAP) == \
        "TABLE 7.1 DESIGN STANDARDS BY DISTRICT"


# --- Rule 4 context anchor: "table" in prose is not a caption/reference -----
#
# Review finding (2026-08-24): the un-anchored rule renumbered ANY "table N.M"
# in prose, including a compound noun like "water table" followed by an
# unrelated measurement. Not hypothetical: "water table" is standard septic/
# soils/groundwater language and a Shoreland article is planned (CLAUDE.md
# Phase 9), so this phrase is very likely to occur followed by a depth in
# feet. A real amendment to that depth must never be silently suppressed.

def test_the_reviewers_water_table_case_is_not_renumbered():
    """THE test for this fix. A genuine numeric amendment inside a phrase that
    merely contains the word 'table' followed by N.M must survive -- not be
    mistaken for a table caption/cross-reference."""
    old = "The seasonal high water table 5.2 feet below grade shall govern."
    new = "The seasonal high water table 6.2 feet below grade shall govern."
    assert norm_old(old) != norm_new(new)


def test_a_second_prose_table_case_is_not_renumbered():
    """A different compound-noun shape, same hazard class: 'rate table 9.1
    percent' is not a table caption or cross-reference either."""
    old = "The applicable tax rate table 9.1 percent applies to this parcel."
    new = "The applicable tax rate table 3.1 percent applies to this parcel."
    assert norm_old(old) != norm_new(new)


def test_but_a_genuine_bare_caption_reference_is_still_suppressed_with_the_anchor():
    """The anchor must not have thrown out real cases along with the hazard:
    a caption/reference immediately followed by sentence punctuation (no
    title text) still suppresses, same as one followed by a title."""
    assert norm_old("See Table 6.1.") == norm_new("See Table 7.1.")
    assert norm_old("per Table 6.1, as applicable.") == norm_new("per Table 7.1, as applicable.")


# --- Rule 5: frontmatter article-number renumbering -------------------------

def test_frontmatter_article_number_renumbering_is_suppressed():
    assert norm_old('article-number: "6"') == norm_new('article-number: "7"')


def test_but_an_unpredicted_frontmatter_article_number_still_differs():
    assert norm_old('article-number: "6"') != norm_new('article-number: "3"')


def test_the_new_side_frontmatter_is_never_renumbered():
    assert norm_new('article-number: "6"') == 'article-number: "6"'


def test_normalize_old_side_also_renumbers_frontmatter():
    assert nz.normalize_old_side('article-number: "6"', amap=AMAP) == 'article-number: "7"'


# --- Rule 3: paragraph re-wrapping ------------------------------------------

def test_rewrapping_is_suppressed():
    wrapped = "1. The proposed subdivision will not\n   result in undue water pollution."
    flat = "1. The proposed subdivision will not result in undue water pollution."
    assert norm_old(wrapped) == norm_old(flat)


def test_but_a_deleted_sentence_still_differs():
    """THE test. If this ever passes trivially the feature is unsafe."""
    keep = "1. Water shall be adequate. Sewage shall be adequate."
    cut = "1. Water shall be adequate."
    assert norm_old(keep) != norm_new(cut)


def test_a_changed_number_still_differs():
    assert norm_old("a 40 ft right-of-way") != norm_new("a 33 ft right-of-way")


def test_shall_to_may_still_differs():
    assert norm_old("The Board shall require") != norm_new("The Board may require")


# --- normalize_old_side: render-safe (no rewrap) ----------------------------
#
# Added after a Task 3 review finding (2026-08-24): the old side of a baseline
# redline is what redline-text.py --source RENDERS, not just compares. Rule 3
# (rewrap) collapses indented continuation lines, which flattens the Code's
# lettered sub-clause hierarchy into run-on prose once it reaches the
# renderer. normalize_old_side applies heading-case + renumbering only.

def test_normalize_old_side_still_suppresses_heading_case():
    assert nz.normalize_old_side("### A. PURPOSE", amap=AMAP) == "### a. PURPOSE"


def test_normalize_old_side_still_renumbers():
    assert nz.normalize_old_side("See Article 7.", amap=AMAP) == "See Article 8."


def test_normalize_old_side_preserves_indentation_on_a_nested_sub_clause_block():
    """THE test for the bug the review caught. A lettered sub-clause list, each
    line indented under its parent, must come out with every line intact --
    not merged into one run-on line the way `normalize()`'s rewrap rule would."""
    block = (
        "1. The reviewing authority may:\n"
        "    a. Determine the application is complete and ready for review.\n"
        "    b. Determine the application is incomplete and deny the application.\n"
        "    c. Determine the application is incomplete and allow withdrawal.\n"
    )
    out = nz.normalize_old_side(block, amap=AMAP)
    assert out == block, "indentation/line structure must be untouched"
    assert out.count("\n") == block.count("\n")


def test_normalize_old_side_does_not_collapse_a_wrapped_paragraph_either():
    """Unlike normalize(), this function must leave line breaks exactly where
    they were -- rewrap is Rule 3 and normalize_old_side never applies it."""
    wrapped = "1. The proposed subdivision will not\n   result in undue water pollution."
    assert nz.normalize_old_side(wrapped, amap=AMAP) == wrapped


def test_normalize_is_not_render_safe_for_the_same_block():
    """Documents the contrast directly: normalize() (comparison-only) DOES
    collapse the block that normalize_old_side (render-safe) leaves alone."""
    block = (
        "1. The reviewing authority may:\n"
        "    a. Determine the application is complete and ready for review.\n"
        "    b. Determine the application is incomplete and deny the application.\n"
    )
    assert norm_old(block) != block
    assert nz.normalize_old_side(block, amap=AMAP) == block


# --- The report --------------------------------------------------------------

def test_report_counts_each_rule_separately():
    old = "### A. PURPOSE\n1. See Article 7."
    new = "### a. PURPOSE\n1. See Article 8."
    r = nz.report(old, new, amap=AMAP)
    assert r["heading_case"] >= 1
    assert r["renumber"] >= 1


# --- The operator's number and the packet's marks are ONE computation --------
# build/adoption_breakdown.py prints the per-article change counts an operator
# reviews before the packet exists; build/redline_resolve.py + redline-text.py
# produce the marks a citizen reads in the packet. Those had two independent
# implementations of "the old side": normalize() (which rewraps) versus
# normalize_old_side() (which does not). They agreed -- 151, identically per
# article -- but nothing asserted it, so the reviewed number could have drifted
# from the shown marks with no test going red. changed_line_count() is now the
# single definition, computed the way the packet is; these tests pin both the
# agreement and the fact that it follows the RENDER path.

def test_changed_line_count_follows_the_render_path():
    """The old side is normalize_old_side()'d, the new side is verbatim --
    exactly what redline_resolve.py writes and what build-redline-full.sh
    stages. If this ever diverges, the count stops describing the packet."""
    old = "### A. PURPOSE\nSee Article 7 and TABLE 6.1 Design Standards.\n"
    new = "### a. PURPOSE\nSee Article 8 and TABLE 7.1 Design Standards.\n"
    expected = nz._marked(nz.normalize_old_side(old, amap=AMAP).splitlines(),
                          new.splitlines())
    assert nz.changed_line_count(old, new, amap=AMAP) == expected
    # And it is genuinely suppressed to zero: heading case + both renumberings.
    assert nz.changed_line_count(old, new, amap=AMAP) == 0


def test_changed_line_count_still_sees_a_real_amendment():
    old = "### A. PURPOSE\nThe applicant shall provide 20 feet.\n"
    new = "### a. PURPOSE\nThe applicant may provide 24 feet.\n"
    assert nz.changed_line_count(old, new, amap=AMAP) == 2


def test_breakdown_and_render_paths_agree_on_the_real_corpus():
    """The agreement the reviewer asked to have asserted rather than assumed:
    across every mappable baseline->current article pair, the comparison-only
    path (normalize() both sides, with rewrap) and the render path
    (changed_line_count) must report the same number PER ARTICLE. If a future
    normaliser rule breaks that, the operator's number and the packet's marks
    have parted company and one of them is lying."""
    import subprocess

    REPO = BUILD.parent
    for cur, base in sorted(AMAP.files.items()):
        if base is None or AMAP.not_text_comparable_reason(cur) is not None:
            continue
        old = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{AMAP.baseline_version}:source/{base}"],
            capture_output=True, text=True)
        assert old.returncode == 0, cur
        new = (REPO / "source" / cur).read_text()

        comparison = nz._marked(
            nz.normalize(old.stdout, amap=AMAP, is_baseline_side=True).splitlines(),
            nz.normalize(new, amap=AMAP, is_baseline_side=False).splitlines())
        render = nz.changed_line_count(old.stdout, new, amap=AMAP)
        assert comparison == render, (
            f"{cur}: the reviewed count ({comparison}) and the rendered count "
            f"({render}) disagree")


# --- The counter counts every changed line ------------------------------------
# changed_line_count dropped diff headers by PREFIX ("---"/"+++"), which also
# dropped real changed lines beginning with -- or ++. Found 2026-10-08.

def test_a_deleted_horizontal_rule_is_counted():
    """`---` deleted appears in the diff as `----`, which the old prefix filter
    discarded as if it were the file header."""
    assert nz.changed_line_count("a\n---\nb\n", "a\nb\n", amap=AMAP) == 1


def test_an_added_line_beginning_with_plus_plus_is_counted():
    assert nz.changed_line_count("a\n", "a\n++x\n", amap=AMAP) == 1


def test_identical_text_still_counts_zero():
    """The fix must not count the headers when there is no diff at all -- an
    empty diff has no header lines to skip."""
    assert nz.changed_line_count("a\nb\n", "a\nb\n", amap=AMAP) == 0


# --- Rule 6: section renumbering ---------------------------------------------
# A section inserted into an Article shifts every later heading and every
# reference to it. Suppressed on the OLD side only, from a DERIVED map
# (build/section_map.py), keyed on the baseline article number read from the
# text's own frontmatter. Every grammar is tested in both directions.

FM = '---\narticle-number: "7"\n---\n'
SMAP = {7: {3: 4, 4: 5, 6: 7, 7: 8, 14: 15}}

# Rule 6 is tested against an IDENTITY article map. The module-level AMAP is the
# pinned v0.1 fixture, which renumbers Article 7 -> 8: under it every test below
# would have its own frontmatter rewritten (and every count would carry one
# extra changed line), failing for a reason that has nothing to do with Rule 6.
# Only the ordering test uses AMAP, deliberately.
IDENTITY = adoption_map.AdoptionMap(baseline_version="v1.0",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})


def old7(body):
    return nz.normalize_old_side(FM + body, amap=IDENTITY, smap=SMAP)


def test_a_renumbered_heading_is_suppressed():
    assert old7("## 3. ADULT ESTABLISHMENT\n") == FM + "## 4. ADULT ESTABLISHMENT\n"


def test_but_a_heading_the_map_does_not_cover_is_untouched():
    assert old7("## 2. EXPANDED USE STANDARDS\n") == FM + "## 2. EXPANDED USE STANDARDS\n"


def test_a_bare_section_reference_is_suppressed():
    assert old7("See Section 3.\n") == FM + "See Section 4.\n"


def test_but_a_bare_reference_to_an_unmapped_section_still_differs():
    assert old7("See Section 5.\n") == FM + "See Section 5.\n"


def test_only_the_leading_number_of_a_dotted_reference_moves():
    assert old7("See Section 3.C.4.\n") == FM + "See Section 4.C.4.\n"


def test_but_a_changed_sub_section_letter_still_differs():
    """Only the section number is normalised; a real change to the letter that
    follows it is untouched and survives the comparison."""
    assert old7("See Section 3.C.4.\n") != FM + "See Section 4.D.4.\n"


def test_each_element_of_a_list_is_mapped_independently():
    assert old7("Sections 6, 7.F, and 14\n") == FM + "Sections 7, 8.F, and 15\n"


def test_a_list_with_and_and_through_is_mapped():
    assert old7("Sections 3 and 6\n") == FM + "Sections 4 and 7\n"
    assert old7("Sections 3.F.2 through 3.F.4\n") == FM + "Sections 4.F.2 through 4.F.4\n"


def test_a_bare_section_sign_is_suppressed():
    assert old7("under §3.\n") == FM + "under §4.\n"


def test_an_explicit_article_reference_resolves_against_THAT_article():
    """`Article 3 Section 2` inside Article 7 means Article 3's section 2,
    not Article 7's."""
    smap = {3: {2: 3}, 7: {2: 9}}
    out = nz.normalize_old_side(FM + "See Article 3 Section 2.\n", amap=IDENTITY, smap=smap)
    assert "Section 3." in out and "Section 9" not in out


def test_an_explicit_article_section_sign_resolves_against_that_article():
    smap = {8: {12: 13}}
    assert nz.normalize_old_side(FM + "under Article 8 §12.F.\n", amap=IDENTITY,
                                 smap=smap).endswith("under Article 8 §13.F.\n")


def test_a_bare_reference_resolves_against_its_OWN_article_not_another():
    """A bare `Section N` is unambiguous only within its Article. Article 3's
    text is not shifted by Article 7's map."""
    fm3 = '---\narticle-number: "3"\n---\n'
    assert nz.normalize_old_side(fm3 + "See Section 3.\n", amap=IDENTITY,
                                 smap={7: {3: 4}}) == fm3 + "See Section 3.\n"


def test_section_of_another_article_is_left_alone():
    assert old7("See Section 3 of Article 4.\n") == FM + "See Section 3 of Article 4.\n"
    assert old7("See Section 3.C.4 of Article 4.\n") == FM + "See Section 3.C.4 of Article 4.\n"


def test_section_of_this_article_resolves_against_the_containing_one():
    assert old7("See Section 3 of this Article.\n") == FM + "See Section 4 of this Article.\n"


def test_without_frontmatter_bare_references_are_not_guessed():
    """No frontmatter, no containing Article: bare forms stay as they are.
    Explicit `Article N Section M` still resolves."""
    assert nz.normalize_old_side("See Section 3.\n", amap=IDENTITY, smap=SMAP) == "See Section 3.\n"


def test_the_section_rule_runs_before_article_renumbering():
    """Keyed on BASELINE numbers. The fixture map shifts Article 7 -> 8; if
    article renumbering ran first, the section lookup would use Article 8's
    sub-map and miss. The ONE Rule 6 test that uses the fixture AMAP, on purpose."""
    out = nz.normalize_old_side(FM + "See Article 7 Section 3.\n", amap=AMAP, smap={7: {3: 4}})
    assert out.endswith("See Article 8 Section 4.\n")


def test_the_new_side_is_never_section_renumbered():
    out = nz.normalize(FM + "See Section 3.\n", amap=IDENTITY, is_baseline_side=False, smap=SMAP)
    assert "Section 3." in out


def test_without_a_map_nothing_changes():
    text = FM + "## 3. ADULT\nSee Section 3 and Sections 6, 7.F, and 14.\n"
    assert nz.normalize_old_side(text, amap=AMAP) == nz.normalize_old_side(text, amap=AMAP, smap=None)
    assert nz.normalize_sections_only(text, smap=None) == text


# --- Statutory citations are never rewritten -----------------------------------

STATUTORY = [
    ("article-01-general.md", ["30-A MRSA Section 4358", "30-A MRSA Section 4404",
                               "38 MRSA Sections 435449"]),
    ("article-03-streets-roads-driveways.md", ["30-A MRSA §4404", "23 MRSA §3022",
                                              "23 MRSA §3021", "23 MRSA §3026-A",
                                              "23 MRSA §704"]),
    ("article-07-use-standards.md", ["Subchapter C, §53.11"]),
    ("article-08-administration.md", ["Chapter187, Section 4401", "Title 23, Section 704",
                                      "Title 38, Section 480-B", "38 M.R.S.A. Section 420-D",
                                      "MRSA Title 38 Section 480-B", "Title 12, Section 8869",
                                      "Title 38, Section 435", "MRSA Title 30 Section 2691",
                                      "Title 30-A Section 4452"]),
    ("article-09-definitions.md", ["50 Stat. 888, Section 8", "23 MRSA §3021",
                                   "23 MRSA §3022"]),
]


def _real(name):
    import subprocess
    r = subprocess.run(["git", "-C", str(BUILD.parent), "show", f"v1.0:source/{name}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, name
    return r.stdout


def _shift_everything():
    """A map that would rewrite EVERY section number in every Article."""
    return {a: {k: k + 1 for k in range(1, 10000)} for a in range(1, 10)}


def test_no_statutory_citation_is_ever_rewritten():
    """Every statutory citation in the Code survives a map that would rewrite
    every number it can reach. Measured set, 2026-10-08 -- including the two
    federal citations in Article 9 that a guard limited to MRSA/M.R.S/Title/
    U.S.C would have renumbered, and `§53.11` in Article 7, which collides with
    a real section number."""
    smap = _shift_everything()
    for name, citations in STATUTORY:
        text = _real(name)
        out = nz.normalize_sections_only(text, smap=smap)
        for cite in citations:
            assert cite in text, f"{name}: fixture citation not in the source: {cite!r}"
            assert cite in out, f"{name}: statutory citation rewritten: {cite!r}"


def test_and_the_same_map_DID_rewrite_internal_references():
    """The positive control. If the rule did nothing at all, every statutory
    citation would survive trivially. Article 3 carries internal references the
    same map must move."""
    text = _real("article-03-streets-roads-driveways.md")
    out = nz.normalize_sections_only(text, smap=_shift_everything())
    assert "Article 8 §20" in text and "Article 8 §21" in out
    assert "(Sections 6, 7.F, and 14)" in text and "(Sections 7, 8.F, and 15)" in out


def test_a_mixed_line_rewrites_its_internal_reference_and_not_its_statute():
    """`23 MRSA §3026-A and Article 8 §27` -- the explicit Article prefix is
    decisive, so the statute guard does not suppress the internal reference."""
    fm3 = '---\narticle-number: "3"\n---\n'
    out = nz.normalize_sections_only(fm3 + "under 23 MRSA §3026-A and Article 8 §27.\n",
                                     smap={3: {3026: 3027}, 8: {27: 28}})
    assert "23 MRSA §3026-A" in out
    assert "Article 8 §28" in out


# --- The negative controls that matter most ------------------------------------

def test_a_real_amendment_beside_a_renumbered_heading_still_counts():
    """THE control for this rule. A renumbered heading is suppressed; a real
    change on the very next line -- shall to may -- must still be counted."""
    old = FM + "## 3. ADULT ESTABLISHMENT\nThe applicant shall comply.\n"
    new = FM + "## 4. ADULT ESTABLISHMENT\nThe applicant may comply.\n"
    assert nz.changed_line_count(old, new, amap=IDENTITY, smap={7: {3: 4}}) == 2


def test_a_retargeted_reference_still_counts():
    """Decision D8. §3 FARMING is inserted, so ADULT moves 3 -> 4. A reference
    that still says `Section 3` now points at FARMING -- different content. The
    map turns the old side's reference into `Section 4`, so it differs."""
    old = FM + "## 3. ADULT\n## 4. AMUSE\nSee Section 3.\n"
    new = FM + "## 3. FARMING\n## 4. ADULT\n## 5. AMUSE\nSee Section 3.\n"
    count = nz.changed_line_count(old, new, amap=IDENTITY, smap={7: {3: 4, 4: 5}})
    assert count == 3          # the inserted heading, and the reference line both ways


def test_the_count_drops_to_the_real_figure_for_an_insertion():
    """Only the inserted section is a real change. Without the map, every
    shifted heading and reference counts too."""
    old = FM + ("## 1. GENERAL\nSee Section 2 and Section 3.\n"
                "## 2. ADULT\nText A. See Section 3.\n"
                "## 3. AMUSE\nText B.\n")
    new = FM + ("## 1. GENERAL\nSee Section 3 and Section 4.\n"
                "## 2. FARMING\nNew text.\n"
                "## 3. ADULT\nText A. See Section 4.\n"
                "## 4. AMUSE\nText B.\n")
    smap = {7: {2: 3, 3: 4}}
    assert nz.changed_line_count(old, new, amap=IDENTITY, smap=smap) == 2  # `## 2. FARMING`, `New text.`
    assert nz.changed_line_count(old, new, amap=IDENTITY) > 2               # the control


def test_the_two_paths_still_agree_with_a_map():
    """normalize() and changed_line_count() must apply the rule identically, or
    the operator's number and the packet's marks part company."""
    old = FM + "## 2. ADULT\nSee Section 2.\n## 3. AMUSE\n"
    new = FM + "## 2. FARMING\n## 3. ADULT\nSee Section 3.\n## 4. AMUSE\n"
    smap = {7: {2: 3, 3: 4}}
    comparison = nz._marked(
        nz.normalize(old, amap=IDENTITY, is_baseline_side=True, smap=smap).splitlines(),
        nz.normalize(new, amap=IDENTITY, is_baseline_side=False, smap=smap).splitlines())
    assert comparison == 1     # the inserted heading; and the paths must agree on it
    assert comparison == nz.changed_line_count(old, new, amap=IDENTITY, smap=smap)
