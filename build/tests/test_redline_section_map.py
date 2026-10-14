"""The derived section map reaches the redline: staging, text and page."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BUILD = TESTS.parent
REPO = BUILD.parent
sys.path.insert(0, str(TESTS))
import section_fixtures as fx  # noqa: E402

VER = "v0.98-draft"
ART7 = "article-07-use-standards.md"


@pytest.fixture(scope="module")
def inserted(tmp_path_factory):
    """A v1.0 tree with one section inserted near the top of Article 7, and its map."""
    root = tmp_path_factory.mktemp("ins")
    tree = fx.copy_full_source(root / "source")
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 2, "PROBE SECTION"))
    smap = root / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(smap)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tree, smap


def _standalone_md(tmp_path, tree, **env):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-redline-standalone.sh", "07", VER, "v1.0"], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(out), **env),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return next(out.glob("*.md")).read_text()


def test_without_the_map_renumbering_reads_as_heading_changes(tmp_path, inserted):
    """The control: this is the noise the map exists to remove."""
    tree, _ = inserted
    assert _standalone_md(tmp_path, tree).count("Heading changed") >= 3


def test_with_the_map_only_the_inserted_section_is_noted(tmp_path, inserted):
    tree, smap = inserted
    md = _standalone_md(tmp_path, tree, SECTION_MAP=str(smap))
    assert md.count("Heading changed") == 0
    assert md.count("*[Heading added]*") == 1                  # the in-text note
    assert md.count("Heading added: “Section 2 — PROBE SECTION”") == 1   # the disclosure bullet
    assert "PROBE SECTION" in md


def test_a_map_for_another_tree_is_refused(tmp_path, inserted):
    _, smap = inserted
    other = fx.copy_full_source(tmp_path / "source")          # no inserted section
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-redline-standalone.sh", "07", VER, "v1.0"], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(other), REDLINE_OUT=str(out),
                                SECTION_MAP=str(smap)), capture_output=True, text=True)
    assert r.returncode != 0 and not out.exists()


def test_a_missing_map_file_is_refused_by_the_stage(tmp_path):
    tree = fx.copy_full_source(tmp_path / "source")
    r = subprocess.run(["bash", "-c",
                        f'source build/redline-stage.sh; '
                        f'czc_redline_stage "{tree}" "{tmp_path}/stage" v1.0 "" "" {ART7}'],
                       cwd=REPO, env=dict(os.environ, CZC_SECTION_MAP=str(tmp_path / "nope.json")),
                       capture_output=True, text=True)
    assert r.returncode != 0


def test_the_integrated_redline_honours_src_dir_and_the_map(tmp_path, inserted):
    tree, smap = inserted
    pdf = tmp_path / "rl.pdf"
    r = subprocess.run(["bash", "build/build-redline-full.sh", VER, "v1.0", "January 1, 2027"],
                       cwd=REPO, env=dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(pdf),
                                          SECTION_MAP=str(smap)), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert pdf.exists()
    import fitz
    text = "".join(p.get_text() for p in fitz.open(pdf))
    assert "PROBE SECTION" in text                 # SRC_DIR was honoured, not source/
