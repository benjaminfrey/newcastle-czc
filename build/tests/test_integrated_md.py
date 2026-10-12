"""build/integrated_md.py -- the integrated Code's honest markdown."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BUILD = TESTS.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(TESTS))

import adopted_residue  # noqa: E402
import integrated_md  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
USE_HEADER = "| Use | Status |"
USE_ROW = re.compile(r"^\| (.+) \| (.+) \|$")


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("im") / "source")


@pytest.fixture(scope="module")
def out(tree):
    return integrated_md.render(tree)


def _frontmatter(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").split("\n")
    assert lines[0] == "---"
    end = lines.index("---", 1)
    return "\n".join(lines[:end + 1])


def _use_rows(text):
    rows, inside = 0, False
    for ln in text.split("\n"):
        if ln == USE_HEADER:
            inside = True
            continue
        if inside and ln.startswith("| :---"):
            continue
        if inside and USE_ROW.match(ln):
            rows += 1
            continue
        inside = False
    return rows


def test_nine_frontmatter_blocks_verbatim_in_article_order(tree, out):
    expected = [_frontmatter(sorted(tree.glob(f"article-0{n}-*.md"))[0]) for n in range(1, 10)]
    found = re.findall(r"(?m)^---\narticle-number: .*\n(?:.*\n)*?---$", out)
    assert found == expected
    assert out.count("\n---\n") + out.startswith("---\n") == 18


def test_no_typst_or_build_comments_remain(out):
    assert "{=typst}" not in out and "<!--" not in out and "#table(" not in out


def test_article_3_tables_are_pipe_tables_and_pointers_sit_at_the_markers(out):
    assert "TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH) | Sight Distance (FT) |" in out
    plates = out.index("the ten Thoroughfare Type pages —")
    ex1 = out.index("Exhibit 3.1, the Thoroughfare Inventory —")
    assert plates < out.index("### d. DRIVEWAY")
    assert plates < ex1 < out.index("### d. CLASSIFICATION RUBRIC")


def test_article_2_appendix_is_present_once_between_articles_2_and_3(out):
    assert out.count("## Appendix — District Standards") == 1
    a = out.index("## Appendix — District Standards")
    start2 = out.index('article-number: "2"')
    start3 = out.index('article-number: "3"')
    assert start2 < a < start3
    appendix = out[a:start3]
    assert len(re.findall(r"(?m)^### \S+ ", appendix)) == 13
    assert _use_rows(appendix) == 819
    # the appendix replaces the pointer: no "not reproduced" note for the district pages
    assert "the thirteen district pages (district standards and use tables) — in the PDF" not in out


def test_article_1_ends_with_the_district_maps_pointer(out):
    seg = out[:out.index('article-number: "2"')].rstrip().removesuffix("---").rstrip()
    assert seg.endswith("*[the District Maps — in the PDF edition; not reproduced in this markdown version.]*")


def test_a_damaged_split_marker_refuses_and_writes_nothing(tmp_path):
    bad = fx.copy_full_source(tmp_path / "source")
    art3 = sorted(bad.glob("article-03-*.md"))[0]
    art3.write_text(art3.read_text().replace("TYPE-PAGES", "TYPE-PAGE"), encoding="utf-8")
    dest = tmp_path / "x.md"
    with pytest.raises(integrated_md.MdError):
        integrated_md.render(bad)
    r = subprocess.run([sys.executable, str(BUILD / "integrated_md.py"), str(bad), str(dest)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "integrated_md: refusing" in r.stderr
    assert not dest.exists() and not list(tmp_path.glob("x.md*"))


def test_a_refusal_only_czc_md_makes_leaves_no_pdf_and_no_md(tmp_path):
    # An unclosed comment passes the PDF stage; only the markdown walker refuses it.
    bad = fx.copy_full_source(tmp_path / "source")
    art7 = sorted(bad.glob("article-07-*.md"))[0]
    art7.write_text(art7.read_text() + "\n<!-- never closed\n", encoding="utf-8")
    rel = tmp_path / "rel"
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.98-draft", "January 1, 2027"], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(bad), OUT_DIR=str(rel)),
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "integrated_md: refusing" in r.stderr
    assert not list(rel.glob("*.pdf")) and not list(rel.glob("*.md"))


def _build(tmp_path, mode, version, date):
    o = tmp_path / mode
    env = dict(os.environ, OUT_DIR=str(o))
    if mode != "draft":
        env.update(ADOPTION_MODE=mode, ADOPTION_EVENT_DATE=date)
    r = subprocess.run(["bash", "build/build-full-czc.sh", version, date], cwd=REPO, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    mds = list(o.glob("*.md"))
    assert len(mds) == 1
    return mds[0]


def test_meeting_and_adopted_markdown_are_byte_identical(tmp_path):
    m = _build(tmp_path, "meeting", "v9.0", "May 1, 2027")
    a = _build(tmp_path, "adopted", "v9.0", "May 1, 2027")
    assert m.name != a.name
    assert m.read_bytes() == a.read_bytes()
    assert adopted_residue.find_residue(a.read_text()) == []


def test_the_draft_markdown_has_no_chrome_residue(tmp_path):
    d = _build(tmp_path, "draft", "v0.98-draft", "January 1, 2027")
    assert adopted_residue.find_residue(d.read_text()) == []
