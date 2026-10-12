"""Every numbered page is bound on the correct side, and its chrome is on the outer edge.

The 2020 Code binds odd pages on the LEFT (wide 90 pt margin left, page number and
Article tab on the right) and even pages on the right. Before this test nothing
asserted a margin side, and the integrated draft shipped with 82 of 113 body pages
mirrored: Typst resolves inside/outside from a unit's own physical page index, so a
unit that starts on an even physical page was bound backwards, and the rotated
Article tab keyed off here().page() without the page offset.

Trees are v1.0 content (stable) with the WORKING-TREE layout units (*.typ) laid
over them, because the layout units are what is under test. Output goes to tmp_path.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pymupdf
import pytest

import section_fixtures as fx

REPO = Path(__file__).resolve().parent.parent.parent

HEADER_BAND_PT = 50      # header chrome sits above this
FOOTER_BAND_TOP_PT = 745  # footer chrome sits below this
TAB_BAND_Y_PT = (130, 220)
# The gutter is 90 pt and the fore-edge margin 44 pt, so 67 pt splits them. Only the
# LEFT edge is judged: every line starts there, whereas the right edge is ragged and
# some tables (Exhibit 3.1) stop short of it. Exhibit 3.1's table pages sit 11 pt
# inside the narrow margin (55 pt), still well clear of the threshold.
GUTTER_THRESHOLD_PT = 67


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    root = tmp_path_factory.mktemp("binding")
    src = fx.copy_full_source(root / "src")
    for typ in (REPO / "source").glob("*.typ"):
        shutil.copy2(typ, src / typ.name)
    return src, root


def _build(cmd, src, out):
    out.mkdir()
    env = dict(os.environ, SRC_DIR=str(src), OUT_DIR=str(out))
    r = subprocess.run(["bash", *cmd], cwd=REPO, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return next(p for p in out.glob("*.pdf") if "Redline" not in p.name)


@pytest.fixture(scope="module")
def integrated(tree):
    src, root = tree
    return pymupdf.open(_build(["build/build-full-czc.sh", "v0.98-draft", "January 1, 2027"],
                               src, root / "int"))


@pytest.fixture(scope="module")
def art2(tree):
    src, root = tree
    return pymupdf.open(_build(["build/build-standalone.sh", "2", "v0.98-draft"],
                               src, root / "a2"))


@pytest.fixture(scope="module")
def art3(tree):
    src, root = tree
    return pymupdf.open(_build(["build/build-standalone.sh", "3", "v0.98-draft"],
                               src, root / "a3"))


_FOOT = re.compile(r"^(\d+)\s*\|\s*\D|\D\s*\|\s*(\d+)$")


def printed_number(page):
    """(footer page number, centre x of its footer line), or None (front matter,
    blanks, covers). The footer reads "N | Newcastle Core Zoning Code" on the left
    or "Newcastle Core Zoning Code | N" on the right."""
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            x0, y0, x1, _ = ln["bbox"]
            if ln["dir"] != (1.0, 0.0) or y0 < FOOTER_BAND_TOP_PT:
                continue
            m = _FOOT.search("".join(s["text"] for s in ln["spans"]).strip())
            if m:
                return int(m.group(1) or m.group(2)), (x0 + x1) / 2
    return None


def body_margins(page):
    """(left whitespace, right whitespace) of horizontal text between the bands."""
    w = page.rect.width
    xs0, xs1 = [], []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            x0, y0, x1, y1 = ln["bbox"]
            if (ln["dir"] != (1.0, 0.0) or y0 < HEADER_BAND_PT or y1 > FOOTER_BAND_TOP_PT
                    or not "".join(s["text"] for s in ln["spans"]).strip()):
                continue
            xs0.append(x0)
            xs1.append(x1)
    return (min(xs0), w - max(xs1)) if xs0 else None


def tab_center_x(page):
    """Centre x of the rotated Article tab, or None when the page carries none."""
    y0, y1 = TAB_BAND_Y_PT
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            x0, ty0, x1, ty1 = ln["bbox"]
            if ln["dir"] != (1.0, 0.0) and y0 <= ty0 and ty1 <= y1 + 40:
                return (x0 + x1) / 2
    return None


def check(doc):
    """Return (pages examined, list of problems)."""
    problems, examined = [], 0
    for i, page in enumerate(doc):
        num = printed_number(page)
        if num is None:
            continue
        n, num_x = num
        examined += 1
        mid = page.rect.width / 2
        outer_left = n % 2 == 0     # even page: binding right, outer edge left
        if (num_x < mid) != outer_left:
            problems.append(f"phys {i + 1} (printed {n}): page number on the wrong edge")
        tx = tab_center_x(page)
        if tx is not None and (tx < mid) != outer_left:
            problems.append(f"phys {i + 1} (printed {n}): Article tab on the wrong edge")
        m = body_margins(page)
        if m is None:
            continue
        left = m[0]
        gutter_left = n % 2 == 1
        if (left >= GUTTER_THRESHOLD_PT) != gutter_left:
            problems.append(f"phys {i + 1} (printed {n}): left whitespace {left:.0f} pt, "
                            f"gutter should be on the {'left' if gutter_left else 'right'}")
    return examined, problems


def _assert_bound(doc, minimum):
    examined, problems = check(doc)
    assert examined >= minimum, f"only {examined} numbered pages examined (expected >= {minimum})"
    assert problems == [], f"{len(problems)} problems among {examined} numbered pages:\n" + "\n".join(problems)


def test_integrated_draft_is_bound_correctly(integrated):
    _assert_bound(integrated, 100)


def test_article_2_standalone_is_bound_correctly(art2):
    _assert_bound(art2, 20)


def test_article_3_standalone_is_bound_correctly(art3):
    _assert_bound(art3, 20)
