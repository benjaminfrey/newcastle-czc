"""build-standalone.sh's redirection seams. Without them a per-Article redline
must either fork the builder or mark files inside source/, which is a
destructive edit to the Code itself."""
import os
import re
import subprocess
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parents[2]
TEST_VERSION = "v0.98-draft"   # well-formed, far outside the release series


def run_standalone(article, version, *, cwd=REPO, **env):
    e = dict(os.environ, **env)
    return subprocess.run(["bash", "build/build-standalone.sh", article, version],
                          cwd=cwd, env=e, capture_output=True, text=True)


def page_texts(pdf):
    d = pymupdf.open(pdf)
    try:
        return [p.get_text() for p in d]
    finally:
        d.close()


def test_out_dir_keeps_the_build_out_of_releases(tmp_path):
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out))
    assert r.returncode == 0, r.stderr
    pdfs = list(out.glob("*.pdf"))
    assert len(pdfs) == 1, f"expected one pdf in {out}, found {pdfs}"
    assert pdfs[0].name == f"Article 7 Use Standards (Standalone {TEST_VERSION}).pdf"
    assert not (REPO / "releases" / TEST_VERSION).exists(), (
        "OUT_DIR was set, yet the build created a release directory")
    assert page_texts(pdfs[0]), "no pages"


def test_src_dir_reads_a_copied_tree(tmp_path):
    """The seam must redirect CONTENT, not just output -- a redline stages a
    marked copy of source/ and builds from it."""
    src = tmp_path / "src"
    subprocess.run(["cp", "-R", str(REPO / "source") + "/.", str(src) + "/"],
                   check=True)
    marker = "ZZQQ-SEAM-PROBE-ZZQQ"
    prose = src / "article-07-use-standards.md"
    prose.write_text(prose.read_text().replace("## 1.", f"{marker}\n\n## 1.", 1))
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, SRC_DIR=str(src), OUT_DIR=str(out))
    assert r.returncode == 0, r.stderr
    text = "\n".join(page_texts(next(out.glob("*.pdf"))))
    assert marker in text, "SRC_DIR was set but the build read the real source/"


def test_out_name_override_renames_the_artifact(tmp_path):
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out),
                       OUT_NAME_OVERRIDE="Probe Name")
    assert r.returncode == 0, r.stderr
    assert (out / "Probe Name.pdf").exists()
    assert (out / "Probe Name.md").exists()


def test_a_failed_build_leaves_no_output_dir(tmp_path):
    """mkdir -p ran before input resolution, so a build that could not start
    still left a shipped-looking directory behind."""
    out = tmp_path / "out"
    r = run_standalone("99", TEST_VERSION, OUT_DIR=str(out))
    assert r.returncode != 0
    assert not out.exists(), "a build that could not start created its output dir"
    # Without this the assertion above is vacuous while OUT_DIR is ignored.
    assert not (REPO / "releases" / TEST_VERSION).exists(), (
        "a build that could not start left a release directory behind")


def test_a_standalone_and_its_redline_coexist_without_ambiguity(tmp_path):
    """NEGATIVE CONTROL for the naming. A release directory holds both a
    standalone and its redline, and the old lookup was
    next(glob("Article N *.pdf")) -- which matches both and picks arbitrarily.
    The redline builder is Wave 3, so its artifact is simulated by name here;
    the name is the whole point."""
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out))
    assert r.returncode == 0, r.stderr
    stem = f"Article 7 Use Standards (Standalone {TEST_VERSION})"
    (out / f"{stem} — Redline.pdf").write_bytes((out / f"{stem}.pdf").read_bytes())

    both = sorted(p.name for p in out.glob("Article 7 *.pdf"))
    assert len(both) == 2, both
    specific = [p for p in out.glob("Article 7 *.pdf") if " — Redline" not in p.name]
    assert len(specific) == 1, f"the lookup is still ambiguous: {specific}"
    assert specific[0].name == f"{stem}.pdf"


def test_after_prose_path_honours_both_seams(tmp_path):
    """Articles 1 and 2 splice a native unit AFTER the prose, a different
    codepath from Article 7's single pass and Article 3's at-marker splice.
    Article 2 is also the most parity-sensitive unit. The claim pinned here is
    that both seams redirect content and output on that path -- deliberately not
    a page count, which would rot."""
    src = tmp_path / "src"
    subprocess.run(["cp", "-R", str(REPO / "source") + "/.", str(src) + "/"],
                   check=True)
    marker = "ZZQQ-ART2-PROBE-ZZQQ"
    prose = src / "article-02-prefatory.md"
    original = prose.read_text()
    assert "## 1. DISTRICTS" in original
    prose.write_text(original.replace("## 1. DISTRICTS",
                                      f"{marker}\n\n## 1. DISTRICTS", 1))
    out = tmp_path / "out"
    r = run_standalone("2", TEST_VERSION, SRC_DIR=str(src), OUT_DIR=str(out))
    assert r.returncode == 0, r.stderr
    stem = f"Article 2 District Standards (Standalone {TEST_VERSION})"
    assert (out / f"{stem}.pdf").exists(), sorted(p.name for p in out.iterdir())
    assert (out / f"{stem}.md").exists()
    assert marker in "\n".join(page_texts(out / f"{stem}.pdf")), (
        "SRC_DIR was set but the after-prose path read the real source/")
    assert marker in (out / f"{stem}.md").read_text()
    assert not (REPO / "releases" / TEST_VERSION).exists()


def make_note(path, pages):
    """A note of `pages` blank pages."""
    d = pymupdf.open()
    for _ in range(pages):
        d.new_page(width=612, height=792)
    d.save(str(path))
    d.close()
    return path


def footer_numbers(pdf):
    """(physical_page, printed_number) for every page whose footer carries one.
    Read from a clipped band at the bottom, because the body text of some pages
    contains bare numbers -- the same trap that nearly made the Article 2 chrome
    test pass vacuously."""
    d = pymupdf.open(pdf)
    try:
        pairs = []
        for i, p in enumerate(d):
            band = pymupdf.Rect(0, p.rect.height - 40, p.rect.width, p.rect.height)
            # Whole words only: the footer also carries the version string
            # ("v0.98-draft"), and a regex over the band text reads its "98".
            nums = [w[4] for w in p.get_text("words", clip=band)
                    if re.fullmatch(r"\d+", w[4])]
            if nums:
                pairs.append((i + 1, int(nums[0])))
        return pairs
    finally:
        d.close()


def test_an_even_front_note_preserves_verso_recto_parity(tmp_path):
    """The note is NOT counted in the page offset, so the opener still prints 1
    and physical = printed + K. Chrome keys off the PRINTED number
    (here().page() + page_offset) while the binding margin follows the PHYSICAL
    page, so the two agree only when K is even."""
    note = make_note(tmp_path / "note.pdf", 2)
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out),
                       STANDALONE_FRONT_NOTE=str(note))
    assert r.returncode == 0, r.stderr
    pdf = next(out.glob("*.pdf"))
    pairs = footer_numbers(pdf)
    assert pairs, "no footer numbers read -- the band or the build is wrong"
    assert pairs[0][1] == 1, f"the opener must still print 1, got {pairs[0]}"
    offsets = {phys - printed for phys, printed in pairs}
    assert offsets == {2}, f"expected a constant offset of 2, got {offsets}"
    wrong = [(phys, printed) for phys, printed in pairs
             if phys % 2 != printed % 2]
    assert wrong == [], (
        f"printed and physical parity disagree on {wrong} -- verso/recto chrome "
        f"is inverted against the binding margin")


def test_an_odd_front_note_is_refused(tmp_path):
    """NEGATIVE CONTROL. Without this the build exits 0 and silently reverses
    the binding margins of the whole extract, and nothing notices."""
    note = make_note(tmp_path / "note.pdf", 1)
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out),
                       STANDALONE_FRONT_NOTE=str(note))
    assert r.returncode != 0, "a one-page front note was accepted"
    assert "1 page" in r.stderr, r.stderr
    # A refusal must leave nothing behind -- not even an empty directory that
    # looks like a shipped release.
    assert not out.exists(), "a refused build created its output dir"
    assert not (REPO / "releases" / TEST_VERSION).exists()


def test_a_missing_front_note_is_refused(tmp_path):
    out = tmp_path / "out"
    r = run_standalone("7", TEST_VERSION, OUT_DIR=str(out),
                       STANDALONE_FRONT_NOTE=str(tmp_path / "nope.pdf"))
    assert r.returncode != 0
    assert "not found" in r.stderr
