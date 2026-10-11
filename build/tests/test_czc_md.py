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


def md(tree, n, mode="draft", version=None):
    if version is None:
        version = VER if mode == "draft" else "v1.0"
    return czc_md.render(n, src_dir=tree, mode=mode, version=version)


def test_frontmatter_keeps_the_article_and_drops_the_footer(base_tree):
    out = md(base_tree, 7)
    assert out.startswith('---\narticle-number: "7"\narticle-name: "Use Standards"\n---\n')
    assert "footer-date" not in out


@pytest.mark.parametrize("mode", ["draft", "meeting", "adopted"])
def test_no_draft_chrome_in_any_mode(base_tree, mode):
    out = md(base_tree, 3, mode, "v1.0" if mode != "draft" else VER)
    assert "Draft v" not in out
    assert "this extract does not govern" in out


def test_only_the_meeting_edition_says_it_is_not_yet_adopted(base_tree):
    # Nothing may sound like adoption before the vote; the frozen packet says NOT YET ADOPTED.
    meeting = md(base_tree, 7, "meeting", "v1.0")
    assert "the Town Meeting edition (v1.0), not yet adopted" in meeting
    assert "not yet adopted" not in md(base_tree, 7, "draft", VER)
    assert "not yet adopted" not in md(base_tree, 7, "adopted", "v1.0")


def test_an_unknown_mode_is_refused(base_tree):
    with pytest.raises(czc_md.MdError, match="mode"):
        md(base_tree, 7, "final")


def test_article_3_tables_are_tables_and_no_typst_or_comments_remain(base_tree):
    out = md(base_tree, 3)
    assert "{=typst}" not in out and "#table(" not in out and "<!--" not in out
    assert "TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH) | Sight Distance (FT) |" in out


def test_article_3_points_to_its_native_pages_where_they_sit(base_tree):
    out = md(base_tree, 3)
    plates = out.index("the ten Thoroughfare Type pages —")
    ex1 = out.index("Exhibit 3.1, the Thoroughfare Inventory —")
    ex2 = out.index("Exhibit 3.2, the Thoroughfare Type Map —")
    # the plates' pointer sits where the TYPE-PAGES marker was: before the Driveway subsection
    assert plates < out.index("### d. DRIVEWAY")
    # the exhibits' pointers sit where STREET-TYPE-EXHIBITS was: after the plates,
    # before the Classification Rubric
    rubric = out.index("### d. CLASSIFICATION RUBRIC")
    assert plates < ex1 < rubric and plates < ex2 < rubric


def test_the_extract_note_reads_as_sentences(base_tree):
    out = md(base_tree, 3)
    assert ("*The PDF edition also contains the ten Thoroughfare Type pages; Exhibit 3.1, "
            "the Thoroughfare Inventory; and Exhibit 3.2, the Thoroughfare Type Map. "
            "They are named below where they appear. "
            "The PDF edition is authoritative for them.*") in out
    assert czc_md._join_labels(["A"]) == "A"
    assert czc_md._join_labels(["A", "B"]) == "A and B"


@pytest.mark.parametrize("mode,version", [
    ("adopted", VER), ("draft", "v1.0"), ("meeting", VER), ("draft", ""),
    ("adopted", ""), ("draft", "banana")])
def test_a_version_that_contradicts_the_mode_is_refused(base_tree, mode, version):
    with pytest.raises(czc_md.MdError, match="version"):
        md(base_tree, 7, mode, version)


def test_an_unclosed_comment_is_refused_with_its_line(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    p = tree / "article-07-use-standards.md"
    p.write_text(p.read_text() + "\n\n<!-- never closed\nmore text\n")
    with pytest.raises(czc_md.MdError, match=r"unclosed.*line \d+"):
        md(tree, 7)


def test_a_missing_conditional_file_drops_only_that_units_pointer(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    (tree / "exhibits/street-types/inventory.json").unlink()
    out = md(tree, 3)
    assert "the ten Thoroughfare Type pages" in out
    assert "Exhibit 3.1, the Thoroughfare Inventory —" not in out
    assert "Exhibit 3.2, the Thoroughfare Type Map —" not in out
    assert "Exhibit 3.1, the Thoroughfare Inventory;" not in out


def test_a_marker_that_is_absent_is_refused(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    p = tree / "article-03-streets-roads-driveways.md"
    p.write_text(p.read_text().replace("STREET-TYPE-EXHIBITS", "SOMETHING-ELSE"))
    with pytest.raises(czc_md.MdError, match="marker"):
        md(tree, 3)


def test_appendix_units_that_are_not_all_after_prose_are_refused(base_tree):
    doc = copy.deepcopy(manifest.load())
    doc["2"]["units"][0]["splice"] = "at-marker:TYPE-PAGES"
    with pytest.raises(czc_md.MdError, match="inside the text"):
        czc_md.render(2, src_dir=base_tree, version=VER, doc=doc)


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
        czc_md.render(2, src_dir=base_tree, version=VER, doc=doc)
    doc = copy.deepcopy(manifest.load())
    doc["7"]["md_completeness"] = "prose-only"
    with pytest.raises(czc_md.MdError):
        czc_md.render(7, src_dir=base_tree, version=VER, doc=doc)


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
                        "--src-dir", str(base_tree), "--mode", "adopted", "--version", VER],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "czc_md: refusing" in r.stderr
    assert not bad.exists()


# --- Article 2's appendix ------------------------------------------------------

import json  # noqa: E402
import re  # noqa: E402

USE_ROW = re.compile(r"^\| (.+) \| (.+) \|$")


def _use_rows(text):
    """(use, status) rows of every use table in the appendix."""
    rows, inside = [], False
    for ln in text.split("\n"):
        if ln == "| Use | Status |":
            inside = True
            continue
        if inside and ln.startswith("| :---"):
            continue
        if inside and USE_ROW.match(ln):
            rows.append(USE_ROW.match(ln).groups())
            continue
        inside = False
    return rows


def test_the_appendix_carries_all_thirteen_districts_and_819_uses(base_tree):
    out = md(base_tree, 2)
    data = json.loads((base_tree / "article-02-data.json").read_text())
    for rec in data:
        assert f"### {rec['code']} {rec['name']}" in out
    rows = _use_rows(out)
    assert len(rows) == 819


def test_every_status_is_in_words_and_matches_the_data(base_tree):
    import use_table_changes as utc
    out = md(base_tree, 2)
    legend = utc.parse_legend((base_tree / "article-02.typ").read_text())
    data = json.loads((base_tree / "article-02-data.json").read_text())
    expected = [(u, utc.status_words(s, legend)) for rec in data
                for col in ("use_col1", "use_col2") for c in rec[col] for u, s in c["entries"]]
    assert _use_rows(out) == expected
    assert ("Retail & Service, General",
            "Residential Companion Permit (CEO) + Special Permit (Planning Board)") in _use_rows(out)
    assert any(s == "Not allowed" for _, s in _use_rows(out))


def test_d4s_split_category_prints_whole(base_tree):
    out = md(base_tree, 2)
    d4 = out[out.index("### D4 VILLAGE RESIDENTIAL"):out.index("### D5 VILLAGE BUSINESS")]
    assert "**TRANSPORTATION & UTILITIES**" in d4
    assert "ITIES**" not in d4.replace("UTILITIES**", "")
    assert "\xad" not in out


def test_the_three_districts_without_a_matrix_say_so(base_tree):
    out = md(base_tree, 2)
    for name in ("SD CONSERVATION", "SD CAMPUS", "SD MARINE"):
        sect = out[out.index(f"### {name}"):]
        sect = sect[:sect.find("\n### ", 1)] if "\n### " in sect[1:] else sect
        assert "No Permitted Buildings matrix." in sect


def test_the_appendix_has_the_legend_and_the_standards(base_tree):
    out = md(base_tree, 2)
    assert "Use Permit — issued by CEO" in out
    assert "**DESCRIPTION**" in out and "**PERMITTED BUILDINGS**" in out
    data = json.loads((base_tree / "article-02-data.json").read_text())
    for rec in data:
        title = rec["use_standards"]["title"]
        assert out.count(f"**{title}**") == 1, title


def test_the_appendix_parses_as_markdown(base_tree):
    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    r = subprocess.run(["pandoc", "-f", "markdown", "-t", "html"], input=md(base_tree, 2),
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.count("<table") > 13 * 7


# --- the standalone build calls czc_md (moved from Task 3) -----------------------

def test_the_standalone_build_writes_the_honest_md(tmp_path, base_tree):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(base_tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = next(out.glob("*.md")).read_text()
    assert "{=typst}" not in m and "this extract does not govern" in m


def test_a_refused_md_leaves_no_release_dir(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    (tree / "article-03-streets-roads-driveways.md").unlink()
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode != 0 and not out.exists()


def test_the_article_2_standalone_md_carries_the_appendix(tmp_path, base_tree):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "02", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(base_tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = next(out.glob("*.md")).read_text()
    assert "## Appendix — District Standards" in m and "### D1 RURAL" in m.upper()


def test_a_refusal_from_czc_md_itself_leaves_no_release_dir(tmp_path, base_tree):
    """The brief's refused-md test removes the prose, which an earlier guard
    catches; this one gets all the way to czc_md and is refused THERE."""
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    p = tree / "article-03-streets-roads-driveways.md"
    p.write_text(p.read_text().replace("STREET-TYPE-EXHIBITS", "SOMETHING-ELSE"))
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode != 0 and "czc_md: refusing" in r.stderr and not out.exists()
