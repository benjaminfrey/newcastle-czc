"""build/czc_md.py -- the honest standalone markdown."""
import copy
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BUILD = TESTS.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(TESTS))

import czc_md  # noqa: E402
import manifest  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
VER = "v0.98-draft"


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


def md(tree, n, mode="draft"):
    return czc_md.render(n, src_dir=tree, mode=mode, version=VER)


def test_frontmatter_keeps_the_article_and_drops_the_footer(base_tree):
    out = md(base_tree, 7)
    assert out.startswith('---\narticle-number: "7"\narticle-name: "Use Standards"\n---\n')
    assert "footer-date" not in out


@pytest.mark.parametrize("mode", ["draft", "meeting", "adopted"])
def test_no_draft_chrome_in_any_mode(base_tree, mode):
    out = md(base_tree, 3, mode)
    assert "Draft v" not in out
    assert "this extract does not govern" in out


def test_an_unknown_mode_is_refused(base_tree):
    with pytest.raises(czc_md.MdError, match="mode"):
        md(base_tree, 7, "final")


def test_article_3_tables_are_tables_and_no_typst_or_comments_remain(base_tree):
    out = md(base_tree, 3)
    assert "{=typst}" not in out and "#table(" not in out and "<!--" not in out
    assert "TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH) | Sight Distance (FT) |" in out


def test_article_3_points_to_its_native_pages_where_they_sit(base_tree):
    out = md(base_tree, 3)
    assert "the ten Thoroughfare Type pages" in out
    assert "Exhibit 3.1, the Thoroughfare Inventory" in out
    assert "Exhibit 3.2, the Thoroughfare Type Map" in out
    # the plates' pointer sits where the TYPE-PAGES marker was: before the Driveway subsection
    plates = out.index("the ten Thoroughfare Type pages —")
    assert out.index("## ") < plates


def test_article_1_names_the_district_maps(base_tree):
    out = md(base_tree, 1)
    assert "the District Maps" in out
    assert "PDF edition" in out


def test_a_pure_prose_article_is_its_text(base_tree):
    out = md(base_tree, 7)
    src = (base_tree / "article-07-use-standards.md").read_text()
    body = src.split("\n---\n", 1)[1]
    assert body.strip() in out


def test_a_table_outside_the_grammar_becomes_a_pointer(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    p = tree / "article-03-streets-roads-driveways.md"
    p.write_text(p.read_text().replace("[20], [155],", "table.cell(colspan: 2)[20],", 1))
    out = md(tree, 3)
    assert "TABLE 3.2 SIGHT DISTANCE — shown in the PDF edition" in out
    assert "#table(" not in out


def test_completeness_that_contradicts_the_units_is_refused(base_tree):
    """The negative control the spec names: claiming 'complete' for an Article
    with native pages would ship the gap silently."""
    doc = copy.deepcopy(manifest.load())
    doc["2"]["md_completeness"] = "complete"
    with pytest.raises(czc_md.MdError, match="complete"):
        czc_md.render(2, src_dir=base_tree, doc=doc)
    doc = copy.deepcopy(manifest.load())
    doc["7"]["md_completeness"] = "prose-only"
    with pytest.raises(czc_md.MdError):
        czc_md.render(7, src_dir=base_tree, doc=doc)


def test_an_appendix_with_no_generator_is_refused(base_tree, monkeypatch):
    monkeypatch.setattr(czc_md, "APPENDICES", {})
    with pytest.raises(czc_md.MdError, match="appendix"):
        md(base_tree, 2)


def test_cli_writes_on_success_and_nothing_on_refusal(base_tree, tmp_path):
    out = tmp_path / "a3.md"
    r = subprocess.run([sys.executable, str(BUILD / "czc_md.py"), "03", str(out),
                        "--src-dir", str(base_tree), "--version", VER],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.read_text().startswith('---\narticle-number: "3"')
    bad = tmp_path / "a2.md"
    r = subprocess.run([sys.executable, str(BUILD / "czc_md.py"), "2", str(bad),
                        "--src-dir", str(base_tree), "--version", VER],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "czc_md: refusing" in r.stderr
    assert not bad.exists()
