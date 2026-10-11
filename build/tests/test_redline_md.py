"""build/redline_md.py -- the integrated redline's markdown edition."""
import os
import re
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
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
VER = "v0.98-draft"


@pytest.fixture(scope="module")
def edited_tree(tmp_path_factory):
    tree = fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")
    f = next(tree.glob("article-07-*.md"))
    text = f.read_text(encoding="utf-8")
    m = re.search(r"\bthe\b", text.split("\n---\n", 1)[1])
    i = text.index("\n---\n") + 5 + m.start()
    f.write_text(text[:i] + "zzqx" + text[i + 3:], encoding="utf-8")
    return tree


def _stage(tree, dest):
    subprocess.run(["bash", "-c",
                    'source build/redline-stage.sh; czc_redline_stage "$1" "$2" v1.0 "" --plain',
                    "_", str(tree), str(dest)], cwd=REPO, check=True)
    return dest


@pytest.fixture(scope="module")
def stage(edited_tree, tmp_path_factory):
    return _stage(edited_tree, tmp_path_factory.mktemp("st") / "plain")


def _run(stage, out):
    return subprocess.run([sys.executable, str(BUILD / "redline_md.py"), str(stage), str(out),
                           "--title", "T — Redline"], capture_output=True, text=True)


def _assert_edition(md, title):
    assert md.split("\n", 1)[0] == f"# {title}"
    assert md.count("Redline key:") == 1
    heads = [re.findall(rf"^# Article {n}\b.*$", md, re.M) for n in range(1, 10)]
    assert all(len(h) == 1 for h in heads), heads
    pos = [md.index(h[0]) for h in heads]
    assert pos == sorted(pos)
    a7 = md[pos[6]:pos[7]]
    assert "1. To ensure ~~the~~**zzqx** health" in a7
    assert "{=typst}" not in md
    assert "<!--" not in md
    assert "TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH)" in md


def test_one_legend_every_article_in_order(stage, tmp_path):
    out = tmp_path / "out.md"
    r = _run(stage, out)
    assert r.returncode == 0, r.stderr
    _assert_edition(out.read_text(encoding="utf-8"), "T — Redline")


def test_a_file_without_its_legend_is_refused(stage, tmp_path):
    st = tmp_path / "st"
    shutil.copytree(stage, st)
    f = next(st.glob("article-05-*.md"))
    t = f.read_text(encoding="utf-8")
    f.write_text(t.replace("Redline key:", "Key:", 1), encoding="utf-8")
    out = tmp_path / "out.md"
    r = _run(st, out)
    assert r.returncode == 1
    assert not out.exists()


def test_differing_legends_are_refused(stage, tmp_path):
    st = tmp_path / "st"
    shutil.copytree(stage, st)
    f = next(st.glob("article-05-*.md"))
    t = f.read_text(encoding="utf-8")
    f.write_text(t.replace("Redline key:", "Redline key: (altered)", 1), encoding="utf-8")
    out = tmp_path / "out.md"
    r = _run(st, out)
    assert r.returncode == 1
    assert not out.exists()


@pytest.mark.parametrize("n", [3, 7])
def test_body_markdown_matches_render(edited_tree, n):
    f = next(edited_tree.glob(f"article-0{n}-*.md"))
    body = czc_md.body_markdown(n, f.read_text(encoding="utf-8"), src_dir=edited_tree)
    assert body.strip() in czc_md.render(n, src_dir=edited_tree, version=VER)


def test_the_integrated_redline_writes_its_md(edited_tree, tmp_path):
    env = dict(os.environ, SRC_DIR=str(edited_tree), REDLINE_OUT=str(tmp_path / "rl.pdf"),
               REDLINE_MD_OUT=str(tmp_path / "rl.md"))
    r = subprocess.run(["bash", str(BUILD / "build-redline-full.sh"), VER, "v1.0", "January 1, 2027"],
                       cwd=REPO, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert (tmp_path / "rl.pdf").exists()
    _assert_edition((tmp_path / "rl.md").read_text(encoding="utf-8"),
                    "Newcastle CZC (Integrated Draft v0.98-draft) — Redline")
    # control: unset => no markdown anywhere
    ctl = tmp_path / "ctl"
    ctl.mkdir()
    env2 = {k: v for k, v in env.items() if k != "REDLINE_MD_OUT"}
    env2["REDLINE_OUT"] = str(ctl / "rl.pdf")
    r = subprocess.run(["bash", str(BUILD / "build-redline-full.sh"), VER, "v1.0", "January 1, 2027"],
                       cwd=REPO, env=env2, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert list(ctl.glob("*.md")) == []


def test_a_refused_markdown_leaves_no_pdf_and_no_md(edited_tree, tmp_path):
    # Damage Article 3's split marker: redline_md refuses. The markdown is assembled
    # BEFORE the PDF build, so the run stops with neither deliverable placed.
    tree = tmp_path / "source"
    shutil.copytree(edited_tree, tree)
    f = next(tree.glob("article-03-*.md"))
    t = f.read_text(encoding="utf-8")
    kept = [ln for ln in t.split("\n") if "TYPE-PAGES" not in ln]
    assert len(kept) < len(t.split("\n"))
    f.write_text("\n".join(kept), encoding="utf-8")
    env = dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(tmp_path / "rl.pdf"),
               REDLINE_MD_OUT=str(tmp_path / "rl.md"))
    r = subprocess.run(["bash", str(BUILD / "build-redline-full.sh"), VER, "v1.0", "January 1, 2027"],
                       cwd=REPO, env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "could not assemble the markdown edition" in r.stderr, r.stderr[-1500:]
    assert not (tmp_path / "rl.pdf").exists()
    assert not (tmp_path / "rl.md").exists()
