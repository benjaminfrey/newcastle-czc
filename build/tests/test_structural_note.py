"""The baseline redline's structural-changes note (ADOPTION-SPEC.md §4.3).

THE DEFECT THIS PINS. build-redline-full.sh hardcoded one cover caveat for both
the draft-to-draft and the baseline runs, mentioning only the figures/tables
limitation. So the packet redline showed Article 2 with ZERO marks and no
renumbering marks anywhere, and said nothing about either. A citizen reads that
as "Article 2 untouched, nothing renumbered." Suppressing ~126 renumbering
marks is honest only if the reader is told once, plainly -- these tests are
what keep that page in the packet.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent
BUILD = REPO / "build"
sys.path.insert(0, str(BUILD))

import structural_note  # noqa: E402
import adoption_map  # noqa: E402


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


def note_text(tmp_path, **kw):
    out = tmp_path / "note.pdf"
    structural_note.build_note(str(out), **kw)
    d = pymupdf.open(out)
    assert d.page_count == 1, (
        "the note must stay ONE page: it is the front matter's verso and the "
        "front-matter page count is parity-critical")
    return d[0].get_text()


def test_note_states_all_three_unmarkable_changes(tmp_path):
    t = note_text(tmp_path)
    low = t.lower()
    # 1. Article 2 unmarked, and explicitly not "untouched".
    assert "article 2" in low
    assert "unmarked" in low
    assert "untouched" in low, (
        "the note must say in words that no marks does NOT mean no change")
    # 2. The renumbering, stated once instead of marked 126 times.
    assert "renumber" in low
    assert "3 becomes 4" in low and "8 becomes 9" in low
    # 3. The pre-existing figures/tables limitation.
    assert "figure" in low and "current state" in low
    # And that Article 3 is wholly new, so its all-red body is not a surprise.
    assert "thoroughfares" in low


def test_note_reads_its_article_map_from_the_data(tmp_path):
    """The page and the suppression must not be able to disagree: the shift
    sentence is generated from adoption-map.json, not restated in prose."""
    m = tmp_path / "map.json"
    m.write_text(json.dumps({
        "baseline_version": "v0.1-baseline",
        "article_numbers": {"1": 1, "2": 3},
        "files": {},
        "not_text_comparable": {},
    }))
    t = note_text(tmp_path, map_path=str(m))
    assert "2 becomes 3" in t
    assert "3 becomes 4" not in t


def test_note_names_the_document_it_compares_against(tmp_path):
    t = note_text(tmp_path, old_label="the Code adopted November 3, 2020")
    assert "November 3, 2020" in t


# --- The parity-critical half ------------------------------------------------
# The note replaces the blank verso between the cover and the TOC. That keeps
# the pre-TOC page count EVEN (invariant 1: the TOC is rendered standalone and
# its binding margins bake in at its own parity) and the front matter EVEN
# (invariant 2: the body's physical parity matches its logical numbering, so
# body page 1 is a recto; Articles are NOT padded to open on a recto, v0.19). A
# note that changed either would silently break chrome across the whole document.

# Front matter: cover, front note (the blank in an ordinary build), 2-page TOC.
FRONT_COUNT = 4
# The footer sits at y ~ 761-773 of a 792 pt page; body text can reach ~735.
FOOTER_BAND_PT = 40
# Verso reads "N | Newcastle Core Zoning Code"; recto "Newcastle Core Zoning Code | N".
FOOTER_NUMBER = re.compile(
    r"Newcastle Core Zoning Code\s*\|\s*(\d+)|(\d+)\s*\|\s*Newcastle Core Zoning Code")


def test_front_note_replaces_the_blank_without_moving_anything(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    note = tmp_path / "note.pdf"
    structural_note.build_note(str(note))

    e = dict(os.environ, OUT_DIR=str(out), FRONT_NOTE_PDF=str(note))
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    # The claim is "the note does not add a page", so compare against the same
    # build without it rather than against a literal that moves every amendment.
    plain_out = tmp_path / "plain"
    plain_out.mkdir()
    rp = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                        cwd=REPO, env=dict(os.environ, OUT_DIR=str(plain_out)),
                        capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr

    plain = d = None
    try:
        plain = pymupdf.open(next(plain_out.glob("*.pdf")))
        d = pymupdf.open(next(out.glob("*.pdf")))
        assert d.page_count == plain.page_count, (
            f"the note changed the page count: {plain.page_count} without it, "
            f"{d.page_count} with it. It takes the place of the blank verso.")
        # Without this the comparison above could pass with the note doing
        # nothing: the page it replaces must be the blank, and in the plain
        # build it must be blank.
        assert not plain[1].get_text().strip(), (
            "the plain build's page 2 is not blank, so there is no blank for "
            "the note to replace")
        assert "HOW TO READ THIS REDLINE" in d[1].get_text(), (
            "the note belongs on the verso facing the cover — before any marked text")
        assert d[1].get_text().strip(), "page 2 is still blank: the note was not inserted"

        # Parity invariant: the printed footer number equals the physical page
        # minus the 4-page front matter (cover, front note, two-page TOC), on
        # EVERY body page — not just the last one, and not a literal that moves
        # with the Code's length. The footer is read from a clipped band at the
        # foot of the page: the wordmark and digits also occur in body text.
        printed = {}
        for i in range(FRONT_COUNT, d.page_count):
            page = d[i]
            band = page.get_text(clip=pymupdf.Rect(
                0, page.rect.height - FOOTER_BAND_PT, page.rect.width, page.rect.height))
            m = FOOTER_NUMBER.search(band)
            printed[i + 1] = int(m.group(1) or m.group(2)) if m else None

        # Non-degeneracy: the check below is vacuous if it parsed nothing.
        body_pages = d.page_count - FRONT_COUNT
        assert body_pages > 0, "no body pages beyond the front matter"
        unparsed = [pg for pg, n in printed.items() if n is None]
        assert unparsed == [], (
            f"body pages with no readable footer number: {unparsed}. Every page "
            f"after the front matter carries one. A footer-less body page may be "
            f"a new structural pad or unit boundary (e.g. the Article 2 "
            f"pad-to-odd) rather than a chrome bug; check the build's page "
            f"structure before the footer code.")

        wrong = {pg: (n, pg - FRONT_COUNT) for pg, n in printed.items()
                 if n != pg - FRONT_COUNT}
        assert wrong == {}, (
            f"footer number != physical page - {FRONT_COUNT} on these pages "
            f"(physical: (printed, expected)): {wrong}. Front matter is "
            f"{FRONT_COUNT} pages and logical must equal physical.")

        # The other side of the same fact: the front matter itself is numberless.
        for i in range(FRONT_COUNT):
            page = d[i]
            band = page.get_text(clip=pymupdf.Rect(
                0, page.rect.height - FOOTER_BAND_PT, page.rect.width, page.rect.height))
            assert FOOTER_NUMBER.search(band) is None, (
                f"physical page {i + 1} is front matter but prints a footer "
                f"number: {band!r}")
    finally:
        for doc in (plain, d):
            if doc is not None:
                doc.close()


# --- Wave 3b: truthful for the whole Code; scoped to one Article ----------------

import pytest  # noqa: E402
import subprocess as _sp  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, str(Path(__file__).resolve().parent))
import section_fixtures as _fx  # noqa: E402

_NOTE = Path(__file__).resolve().parent.parent / "structural_note.py"
_SHIPPED_MAP = Path(__file__).resolve().parent.parent / "adoption-map.json"
_PRE_ROLLOVER = Path(__file__).resolve().parent / "fixtures" / "adoption-map-v0.1-baseline.json"


def _note(tmp_path, *args, name="n.pdf"):
    out = tmp_path / name
    r = _sp.run([_sys.executable, str(_NOTE), str(out), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = pymupdf.open(out)
    try:
        return "\n".join(p.get_text() for p in d), len(d)
    finally:
        d.close()


def test_the_identity_map_note_claims_nothing_false(tmp_path):
    """The NEGATIVE CONTROL the spec names: under the shipped identity map
    (baseline v1.0, nothing new, nothing non-comparable, nothing renumbered)
    the note must not say any Article is new, unmarked or renumbered. Before
    this wave it said all three, unconditionally."""
    text, _ = _note(tmp_path, "--map", str(_SHIPPED_MAP))
    assert "is new" not in text
    assert "UNMARKED" not in text
    assert "were renumbered" not in text
    assert "Three real changes" not in text
    assert "March 24, 2025" not in text
    assert "HOW TO READ THIS REDLINE" in text                     # the control: it rendered


def test_the_pre_rollover_map_still_discloses_all_three(tmp_path):
    text, pages = _note(tmp_path, "--map", str(_PRE_ROLLOVER))
    assert "Article 3" in text and "is new" in text
    assert "UNMARKED" in text
    assert "3 becomes 4" in text
    assert pages == 1


def test_pad_to_even(tmp_path):
    _, pages = _note(tmp_path, "--map", str(_PRE_ROLLOVER), "--pad-to-even")
    assert pages == 2


@pytest.fixture
def tree(tmp_path):
    return _fx.copy_full_source(tmp_path / "source")


def test_an_article_note_names_what_changed(tmp_path, tree):
    p = tree / "article-07-use-standards.md"
    p.write_text(p.read_text().replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1))
    md = tmp_path / "n.md"
    text, pages = _note(tmp_path, "--scope", "article:7", "--old", "v1.0",
                        "--new-dir", str(tree), "--md", str(md), "--pad-to-even")
    assert pages % 2 == 0
    assert "Article 7" in text and "Use Standards" in text
    assert "its headings" in text
    assert "“Section 5 — AMUSEMENT, OUTDOOR”" in text and "“Section 5 — AMUSEMENT, OUTSIDE”" in text
    assert md.read_text().startswith("## How to read this redline")
    assert "Section 5 — AMUSEMENT, OUTSIDE" in md.read_text()


def test_an_unchanged_article_says_so(tmp_path, tree):
    text, _ = _note(tmp_path, "--scope", "article:7", "--old", "v1.0", "--new-dir", str(tree))
    assert "No change was found in this Article." in text


def test_the_article_2_note_names_the_district_pages_and_the_use_table_document(tmp_path, tree):
    text, pages = _note(tmp_path, "--scope", "article:2", "--old", "v1.0",
                        "--new-dir", str(tree), "--pad-to-even")
    assert "the thirteen district pages" in text
    assert pages % 2 == 0
    # Unchanged tree: the pointer to the Use Table Changes document would send a
    # resident looking for changes that do not exist.
    assert "Use Table Changes" not in text
    # Flip one use-table cell: now the pointer must appear.
    import json
    dp = tree / "article-02-data.json"
    data = json.loads(dp.read_text())
    cell = data[0]["use_col1"][0]["entries"][0]
    cell[1] = "sp" if cell[1] != "sp" else "ex"
    dp.write_text(json.dumps(data, indent=1))
    text2, _ = _note(tmp_path, "--scope", "article:2", "--old", "v1.0",
                     "--new-dir", str(tree), name="n2.pdf")
    assert "Use Table Changes" in text2
    assert "the data its pages are printed from" in text2


def test_a_table_only_change_is_named_on_the_page(tmp_path, tree):
    p = tree / "article-03-streets-roads-driveways.md"
    t = p.read_text()
    start = t.index("```{=typst}", t.index("b. To a point 4 ft above ground"))
    p.write_text(t[:start] + t[start:].replace("\n#", "\n// edited\n#", 1))
    text, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree))
    assert "its tables or figures" in text
    assert "TABLE 3.2 SIGHT DISTANCE" in text


def test_an_article_scope_needs_an_old_ref(tmp_path):
    r = _sp.run([_sys.executable, str(_NOTE), str(tmp_path / "n.pdf"), "--scope", "article:7"],
                capture_output=True, text=True)
    assert r.returncode != 0 and "--old" in r.stderr


# --- Fix round 1 ----------------------------------------------------------------

def _flat(s):
    return " ".join(s.split())


@pytest.mark.parametrize("map_path", [_SHIPPED_MAP, _PRE_ROLLOVER])
def test_the_code_note_names_every_unmarked_page_and_stays_one_page(tmp_path, map_path):
    """The note promises in-text notes for changed tables and figures; the data
    pages (district pages, Type plates, Exhibits 3.1/3.2, District Maps) NEVER get
    one, so the page must name them -- under the identity map too, where nothing
    else says the district pages are unmarked."""
    text, pages = _note(tmp_path, "--map", str(map_path))
    flat = _flat(text)
    assert pages == 1
    assert "Pages shown as they now stand, without marks" in flat
    for label in ("the District Maps (Article 1)", "the thirteen district pages",
                  "the ten Thoroughfare Type pages", "Exhibit 3.1, the Thoroughfare Inventory",
                  "Exhibit 3.2, the Thoroughfare Type Map"):
        assert label in flat, label


def test_the_code_note_refuses_rather_than_spilling_to_a_second_page():
    import adoption_map as am
    blocks = structural_note.note_blocks(am.load(str(_PRE_ROLLOVER)), "the old Code")
    blocks.append(("A far too long block", "word " * 400))
    out = Path(os.devnull)
    with pytest.raises(SystemExit) as e:
        structural_note.render(str(out), None, blocks, intro=structural_note.CODE_INTRO,
                               max_pages=1, pad_to_even=False, scope_name="the whole-Code note")
    assert "overflowed" in str(e.value) and "A far too long block" in str(e.value)


def test_a_needs_call_article_says_so_in_resident_words(tmp_path, tree):
    p = tree / "cross-section-plates.typ"
    p.write_text(p.read_text() + "\n// a layout-only edit\n")
    text, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree))
    flat = _flat(text)
    assert "needs a person's judgement" in flat
    assert "the ten Thoroughfare Type pages" in flat and ".typ" not in flat


def test_a_long_heading_list_flows_and_never_refuses(tmp_path, tree):
    import czc_diff
    name = "article-07-use-standards.md"
    p = tree / name
    old_text = p.read_text()
    p.write_text(_fx.insert_section(old_text, 3, "AGRICULTURE"))     # no section map: many changes
    sc = czc_diff.structural_changes(old_text, p.read_text())
    total = (len(sc["headings_added"]) + len(sc["headings_removed"])
             + len(sc["headings_changed"]) + len(sc["tables_added"])
             + len(sc["tables_removed"]) + len(sc["tables_changed"]))
    assert total > 60, "the fixture must produce a long list"
    md = tmp_path / "n.md"
    text, pages = _note(tmp_path, "--scope", "article:7", "--old", "v1.0",
                        "--new-dir", str(tree), "--md", str(md))
    assert pages <= 4
    shown = text.count("•")
    m = re.search(r"…and (\d+) more\. The full list is in the markdown version", _flat(text))
    if m:
        assert shown + int(m.group(1)) == total
    else:
        assert shown == total
    assert len(re.findall(r"^- ", md.read_text(), re.M)) == total      # the md has them all


def test_a_list_too_long_for_four_pages_ends_with_an_exact_count(tmp_path):
    """The path the Article 7 fixture does not reach (it fits in 4 pages): when
    items remain after the last permitted page, the page says how many."""
    items = [f"• Heading added: “Section {i} — SOMETHING”" for i in range(1, 401)]
    blocks = [("What changed in this Article", "A short block."),
              ("Headings, tables and figures", "\n".join(items))]
    out = tmp_path / "long.pdf"
    pages = structural_note.render(str(out), "Article 7 — Use Standards", blocks,
                                   intro=structural_note.ARTICLE_INTRO, max_pages=4,
                                   pad_to_even=False, scope_name="the Article 7 note")
    assert pages == 4
    d = pymupdf.open(out)
    try:
        text = "\n".join(p.get_text() for p in d)
    finally:
        d.close()
    m = re.search(r"…and (\d+) more\. The full list is in the markdown version", _flat(text))
    assert m, "the last page must say that items remain"
    assert text.count("•") + int(m.group(1)) == 400


# --- Final-review fix wave -------------------------------------------------------

def _tag_tree(tmp_path, ref, name="tagsrc"):
    return _fx.copy_full_source(tmp_path / name, ref)


@pytest.mark.parametrize("n,old,new", [(3, "v0.23-draft", "v0.24-draft"),
                                        (2, "v0.24-draft", "v1.0")])
def test_a_data_only_change_is_never_called_unchanged(tmp_path, n, old, new):
    """I1: Article 3 v0.23->v0.24 rewrote Exhibit 3.1's inventory; Article 2
    v0.24->v1.0 changed the use tables. Neither changed a heading, table or figure
    WRITTEN IN THE TEXT, and the page must not say nothing of the Article changed."""
    tree = _tag_tree(tmp_path, new)
    text, _ = _note(tmp_path, "--scope", f"article:{n}", "--old", old, "--new-dir", str(tree))
    flat = _flat(text)
    assert ("None of the headings, tables or figures written in this Article's text was "
            "added, removed or changed.") in flat
    assert "None of this Article's headings, tables or figures" not in flat
    assert "Its data-driven pages changed: see “Shown in their current form” above." in flat


def test_an_unchanged_article_does_not_claim_data_pages_changed(tmp_path, tree):
    text, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree))
    assert "Its data-driven pages changed" not in _flat(text)


def test_neither_scope_promises_a_note_for_every_table_or_figure(tmp_path, tree):
    """I2: native pages never get an in-text note, so the promise is for a heading,
    or a table or figure written within the text."""
    code, _ = _note(tmp_path, "--map", str(_SHIPPED_MAP))
    art, _ = _note(tmp_path, "--scope", "article:7", "--old", "v1.0", "--new-dir", str(tree),
                   name="a.pdf")
    for scope, text in (("code", code), ("article", art)):
        flat = _flat(text)
        assert "a heading, or a table or figure written within the text," in flat, scope
        assert "Where a heading, table" not in flat, scope


def test_the_markdown_describes_the_markdown(tmp_path, tree):
    """I3 + I4: the .md is read with bold additions and has none of the
    data-driven pages; the PDF keeps its own wording."""
    md, md_code = tmp_path / "a.md", tmp_path / "c.md"
    pdf_text, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree),
                        "--md", str(md))
    _note(tmp_path, "--map", str(_SHIPPED_MAP), "--md", str(md_code), name="c.pdf")
    for path in (md, md_code):
        flat = _flat(path.read_text())
        assert "bold" in flat and "shown in red" not in flat, path
        assert "this markdown version does not include them" in flat, path
    assert "In the PDF they appear as they now stand, without marks:" in _flat(md.read_text())
    flat_pdf = _flat(pdf_text)
    assert "shown in red" in flat_pdf and "markdown version does not include" not in flat_pdf
    assert "they appear as they now stand" in flat_pdf


def test_a_needs_call_item_names_the_label_and_never_a_file(tmp_path, tree):
    """M1."""
    p = tree / "cross-section-plates.typ"
    p.write_text(p.read_text() + "\n// a layout-only edit\n")
    q = tree / "article-02.typ"
    q.write_text(q.read_text() + "\n// a layout-only edit\n")
    t3, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree))
    t2, _ = _note(tmp_path, "--scope", "article:2", "--old", "v1.0", "--new-dir", str(tree),
                  name="n2.pdf")
    for t in (t3, t2):
        assert ".typ" not in t and ".json" not in t
    assert "the ten Thoroughfare Type pages" in _flat(t3)
    assert "))" not in t2 and ") (" not in t2


_STAGE_SH = Path(__file__).resolve().parent.parent / "redline-stage.sh"


def _page_and_text_heading_counts(tmp_path, old, new, n, *extra):
    """(items listed on the page, notes in the text) for one Article, in the
    ordinary draft-to-draft path."""
    nn = f"{n:02d}"
    tree = _fx.copy_full_source(tmp_path / f"src-{old}-{new}", new)
    prose = next(tree.glob(f"article-{nn}-*.md")).name
    md = tmp_path / "n.md"
    _note(tmp_path, "--scope", f"article:{n}", "--old", old, "--new-dir", str(tree),
          "--md", str(md), *extra)
    page = len(re.findall(r"^- Heading (?:added|removed|changed)", md.read_text(), re.M))
    stage = tmp_path / "stage"
    r = _sp.run(["bash", "-c", f'source "{_STAGE_SH}"; czc_redline_stage "{tree}" "{stage}" '
                               f'"{old}" "" "--plain" "{prose}"'],
                capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2])
    assert r.returncode == 0, r.stderr
    text = len(re.findall(r"^\*\[(?:Heading (?:added|removed|changed)|Article title changed)",
                          (stage / prose).read_text(), re.M))
    return page, text


@pytest.mark.parametrize("old,new,nonzero", [("v0.2-draft", "v0.2.1-draft", False),
                                              ("v0.14-draft", "v0.15-draft", True)])
def test_the_page_reads_the_same_old_side_as_the_text(tmp_path, old, new, nonzero):
    """I6: the page normalised the old side's heading letters; the draft-path stage
    marks the raw old text. Before the fix v0.2->v0.2.1 listed dozens of heading
    changes the text never noted."""
    page, text = _page_and_text_heading_counts(tmp_path, old, new, 3)
    assert page == text, f"the page lists {page} heading changes, the text notes {text}"
    if nonzero:
        assert page > 0, "the control: this pair really changes headings"


def test_the_page_takes_the_stages_section_map_and_baseline_flag(tmp_path, tree):
    """For P13: the page must read the old side the stage reads, so it accepts the
    stage's --section-map, and --baseline for the baseline stage."""
    import json
    import section_map
    name = "article-07-use-standards.md"
    p = tree / name
    p.write_text(_fx.insert_section(p.read_text(), 3, "AGRICULTURE"))
    mp = tmp_path / "smap.json"
    mp.write_text(json.dumps(section_map.derive("v1.0", tree)))
    counts = {}
    for label, extra in (("map", ["--section-map", str(mp)]), ("nomap", []),
                         ("baseline", ["--baseline", "--section-map", str(mp)])):
        md = tmp_path / f"{label}.md"
        _note(tmp_path, "--scope", "article:7", "--old", "v1.0", "--new-dir", str(tree),
              "--md", str(md), *extra, name=f"{label}.pdf")
        counts[label] = len(re.findall(r"^- Heading", md.read_text(), re.M))
    assert counts["map"] == 1, counts           # only the inserted section
    assert counts["nomap"] > 50, counts         # the control: without the map every shift counts
    assert counts["baseline"] == 1, counts
