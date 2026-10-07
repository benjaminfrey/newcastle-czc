"""build-standalone.sh's redirection seams. Without them a per-Article redline
must either fork the builder or mark files inside source/, which is a
destructive edit to the Code itself."""
import os
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
