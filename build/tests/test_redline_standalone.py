"""build-redline-standalone.sh: the one-Article redline, in .pdf and .md, with a
generated "How to read this redline" page in front."""
import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import section_fixtures as fx  # noqa: E402
from test_standalone_seams import footer_numbers  # noqa: E402

REPO = TESTS.parent.parent
SCRIPT = REPO / "build" / "build-redline-standalone.sh"
VER = "v0.98-draft"
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"
RED = 0xCC0000


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture
def tree(tmp_path, base_tree):
    import shutil
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def redline(tmp_path, tree, nn, old="v1.0", **env):
    out = tmp_path / "out"
    e = dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(out), **env)
    r = subprocess.run(["bash", str(SCRIPT), nn, VER, old], capture_output=True, text=True,
                       cwd=REPO, env=e)
    assert r.returncode == 0, r.stderr
    pdf = next(out.glob("*.pdf"))
    return pdf, pdf.with_suffix(".md")


def note_pages(pdf):
    """Leading pages with no footer number: the uncounted disclosure note."""
    pairs = footer_numbers(pdf)
    return pairs[0][0] - 1


def parity_violations(pdf):
    pairs = footer_numbers(pdf)
    k = note_pages(pdf)
    return [(phys, printed) for phys, printed in pairs
            if phys - printed != k or phys % 2 != printed % 2]


def red_spans(pdf, from_page):
    d = pymupdf.open(pdf)
    try:
        return [s["text"] for p in list(d)[from_page:]
                for b in p.get_text("dict")["blocks"] for line in b.get("lines", [])
                for s in line["spans"] if s["color"] == RED and s["text"].strip()]
    finally:
        d.close()


def text_of(pdf):
    d = pymupdf.open(pdf)
    try:
        return "\n".join(p.get_text() for p in d)
    finally:
        d.close()


def test_article_7_redline_is_marked_and_keeps_parity(tmp_path, tree):
    p = tree / ART7
    t = p.read_text()
    t = t.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    t = t.replace("## 3. ADULT ESTABLISHMENT\n", "## 3. ADULT ESTABLISHMENT\n\nA new sentence.\n", 1)
    p.write_text(t)
    pdf, md = redline(tmp_path, tree, "07")
    k = note_pages(pdf)
    assert k >= 2 and k % 2 == 0
    assert footer_numbers(pdf)[0][1] == 1
    assert parity_violations(pdf) == []
    assert red_spans(pdf, k), "the added sentence must be marked red"
    body = text_of(pdf)
    assert "HOW TO READ THIS REDLINE" in body
    assert "Heading changed" in body
    m = md.read_text()
    assert "{=typst}" not in m and "rgb(" not in m
    assert "## How to read this redline" in m and "**" in m
    assert "*[Heading changed — it read: “5. AMUSEMENT, OUTDOOR”]*" in m


def test_the_parity_check_sees_an_uncounted_page(tmp_path, tree):
    """The second control: the predicate must be able to fail."""
    p = tree / ART7
    p.write_text(p.read_text().replace("## 3. ADULT ESTABLISHMENT\n",
                                       "## 3. ADULT ESTABLISHMENT\n\nA new sentence.\n", 1))
    pdf, _ = redline(tmp_path, tree, "07")
    d = pymupdf.open(pdf)
    d.new_page(pno=note_pages(pdf) + 1, width=612, height=792)
    broken = tmp_path / "broken.pdf"
    d.save(broken)
    d.close()
    assert parity_violations(broken) != []


def test_article_2_keeps_d1_on_a_verso(tmp_path, tree):
    p = tree / "article-02-prefatory.md"
    t = p.read_text()
    p.write_text(t.replace("\n\n", "\n\nAn added sentence in the prefatory text.\n\n", 2))
    pdf, _ = redline(tmp_path, tree, "02")
    d = pymupdf.open(pdf)
    try:
        first = next(i for i, pg in enumerate(d) if "LOT DIMENSIONS" in pg.get_text())
    finally:
        d.close()
    assert (first + 1) % 2 == 0, f"D1 is on physical page {first + 1}, a recto"
    assert parity_violations(pdf) == []


def test_a_table_only_change_has_no_red_mark_and_says_so(tmp_path, tree):
    """The spec's NEGATIVE CONTROL: a reader who sees no marks concludes nothing
    changed. The page and the text must both say a table changed."""
    p = tree / ART3
    t = p.read_text()
    start = t.index("```{=typst}", t.index("b. To a point 4 ft above ground"))
    p.write_text(t[:start] + t[start:].replace("\n#", "\n// edited\n#", 1))
    pdf, md = redline(tmp_path, tree, "03")
    assert red_spans(pdf, note_pages(pdf)) == []
    body = text_of(pdf)
    assert "Table or figure changed" in body                       # on the page and in the text
    flat = " ".join(body.split())    # the in-text note wraps mid-label in two columns
    assert flat.count("TABLE 3.2 SIGHT DISTANCE") >= 3              # page + note + the table itself
    assert "*[Table or figure changed — shown in its current form, not marked: “TABLE 3.2 SIGHT DISTANCE”]*" in md.read_text()


def test_an_edited_type_pages_line_still_seats_the_plates_in_place(tmp_path, tree):
    """P3's interaction: the marker line's comment text changes, the token stays.
    The first Type plate must sit where it sits in an unmarked build, plus the note."""
    p = tree / ART3
    t = p.read_text()
    line = next(ln for ln in t.splitlines() if "TYPE-PAGES" in ln)
    p.write_text(t.replace(line, line.replace("<!--", "<!-- (edited)"), 1))
    pdf, _ = redline(tmp_path, tree, "03")
    plain = tmp_path / "plain"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), OUT_DIR=str(plain)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    def first_plate(path):
        d = pymupdf.open(path)
        try:
            return next(i for i, pg in enumerate(d) if "MAIN STREET" in pg.get_text()
                        and "S1" in pg.get_text())
        finally:
            d.close()
    assert first_plate(pdf) == first_plate(next(plain.glob("*.pdf"))) + note_pages(pdf)


def test_a_dry_run_leaves_releases_untouched(tmp_path, tree):
    before = subprocess.run(["git", "status", "--porcelain", "--", "releases/"], cwd=REPO,
                            capture_output=True, text=True).stdout
    redline(tmp_path, tree, "09")
    after = subprocess.run(["git", "status", "--porcelain", "--", "releases/"], cwd=REPO,
                           capture_output=True, text=True).stdout
    assert before == after
    assert not (REPO / "releases" / VER).exists()


def test_the_output_names_are_the_standalone_redline_names(tmp_path, tree):
    pdf, md = redline(tmp_path, tree, "07")
    assert pdf.name.endswith(" — Redline.pdf") and md.name.endswith(" — Redline.md")
    assert "Article 7" in pdf.name
