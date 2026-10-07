"""czc_redline_stage: the one place that knows redline_resolve.py's return-code
contract. rc 3 = empty old side (whole body marks as added); rc 4 = old copied
from new (renders unmarked); anything else refuses. Copied into a second script
those three mappings drift, and the drift is silent in the direction that
misleads -- adoption_map.py:6-9 records that exact measured failure.

The second half guards the --plain hazard: plain output carries a legend line
and whole-line sigils that are right in a published .md and wrong in a PDF."""
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STAGE_SH = REPO / "build" / "redline-stage.sh"
V01_MAP = REPO / "build" / "tests" / "fixtures" / "adoption-map-v0.1-baseline.json"


def stage(src, dest, old_ver, *basenames, baseline="", plain="", env=None):
    args = " ".join(f'"{b}"' for b in basenames)
    script = (f'source "{STAGE_SH}"; '
              f'czc_redline_stage "{src}" "{dest}" "{old_ver}" "{baseline}" "{plain}" {args}')
    e = dict(os.environ, **(env or {}))
    return subprocess.run(["bash", "-c", script], cwd=REPO, capture_output=True,
                          text=True, env=e)


def copy_source(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run(["cp", "-R", str(REPO / "source") + "/.", str(src) + "/"], check=True)
    return src


def test_one_basename_marks_only_that_file(tmp_path):
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    r = stage(src, dest, "v1.0", "article-07-use-standards.md")
    assert r.returncode == 0, r.stderr
    for other in ("article-04-site-standards.md", "article-09-definitions.md"):
        assert (dest / other).read_text() == (REPO / "source" / other).read_text(), (
            f"{other} was marked, but only one basename was requested")


def test_native_units_are_copied_verbatim(tmp_path):
    """The .typ/json/svg must reach the stage untouched so every figure renders
    at its current state."""
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    r = stage(src, dest, "v1.0", "article-07-use-standards.md")
    assert r.returncode == 0, r.stderr
    for f in ("article-02.typ", "article-02-data.json",
              "exhibits/cross-sections/types.json"):
        assert (dest / f).read_bytes() == (REPO / "source" / f).read_bytes()


def test_the_summary_line_counts_what_it_marked(tmp_path):
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    r = stage(src, dest, "v1.0", "article-07-use-standards.md")
    assert "Marked 1 article markdown file(s) (vs v1.0)." in r.stdout, r.stdout


def test_default_marks_every_article(tmp_path):
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    r = stage(src, dest, "v1.0")
    assert r.returncode == 0, r.stderr
    assert "Marked 9 article markdown file(s) (vs v1.0)." in r.stdout, r.stdout


def test_an_unresolvable_old_side_refuses_and_leaves_the_stage_clean(tmp_path):
    """NEGATIVE CONTROL: no half-marked tree. redline_resolve.py already
    refuses (exit 1); the extraction must not swallow it.

    Fixture shape matches adoption_map.load(): not_text_comparable is a dict
    (basename -> reason), not a list. new_at_this_adoption is not read by the
    loader but is part of the shipped map's shape."""
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    amap = tmp_path / "bad-map.json"
    amap.write_text(json.dumps({
        "baseline_version": "v1.0",
        "article_numbers": {str(n): n for n in range(1, 10)},
        "files": {"article-07-use-standards.md": "no-such-article.md"},
        "new_at_this_adoption": [],
        "not_text_comparable": {},
    }))
    r = stage(src, dest, "v1.0", "article-07-use-standards.md",
              baseline="--baseline", env={"ADOPTION_MAP": str(amap)})
    assert r.returncode != 0, "an unresolvable old side was accepted"
    assert "could not resolve the old side" in r.stderr, r.stderr
    assert (dest / "article-07-use-standards.md").read_text() == \
        (src / "article-07-use-standards.md").read_text(), "the stage was half-marked"


# -- the rc 3 / rc 4 mappings: a swap of either must fail one of these --------

def test_rc3_new_article_marks_the_whole_body_as_added(tmp_path):
    """article-03 is new since the 2020 baseline (map says null). rc 3 -> empty
    old side -> the whole body is marked, so the staged file must DIFFER from
    its source. If rc 3 were mapped to 'copy new -> old' it would be unmarked."""
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    name = "article-03-streets-roads-driveways.md"
    r = stage(src, dest, "v0.1-baseline", name, baseline="--baseline",
              env={"ADOPTION_MAP": str(V01_MAP)})
    assert r.returncode == 0, r.stderr
    assert f"({name} is new since v0.1-baseline — whole body marked as added)" in r.stdout
    assert (dest / name).read_text() != (src / name).read_text(), \
        "a NEW article came out unmarked"


def test_rc4_not_text_comparable_renders_unmarked(tmp_path):
    """article-02-prefatory moved into a native-Typst unit. rc 4 -> old copied
    from new -> NO marks, so the staged file must equal its source. If rc 4 were
    mapped to 'empty old side' the whole Article would show as added."""
    src = copy_source(tmp_path)
    dest = tmp_path / "stage"
    name = "article-02-prefatory.md"
    r = stage(src, dest, "v0.1-baseline", name, baseline="--baseline",
              env={"ADOPTION_MAP": str(V01_MAP)})
    assert r.returncode == 0, r.stderr
    assert f"({name} is not text-comparable against v0.1-baseline — rendered unmarked)" in r.stdout
    assert (dest / name).read_text() == (src / name).read_text(), \
        "a not-text-comparable article was marked"


# -- the --plain hazard ---------------------------------------------------------

SENTINEL = ".redline-plain-marked"


def test_plain_staging_is_labelled_and_ordinary_staging_is_not(tmp_path):
    src = copy_source(tmp_path)
    plain = tmp_path / "plain"
    r = stage(src, plain, "v1.0", "article-07-use-standards.md", plain="--plain")
    assert r.returncode == 0, r.stderr
    # The hazard is real: the legend is in the staged file.
    assert "Redline key:" in (plain / "article-07-use-standards.md").read_text()
    assert (plain / SENTINEL).exists(), "plain-marked stage carries no label"
    ordinary = tmp_path / "ordinary"
    r = stage(src, ordinary, "v1.0", "article-07-use-standards.md")
    assert r.returncode == 0, r.stderr
    assert not (ordinary / SENTINEL).exists()
    assert "Redline key:" not in (ordinary / "article-07-use-standards.md").read_text()


def _plain_stage(tmp_path):
    src = copy_source(tmp_path)
    plain = tmp_path / "plain"
    r = stage(src, plain, "v1.0", "article-07-use-standards.md", plain="--plain")
    assert r.returncode == 0, r.stderr
    return plain


def test_the_integrated_builder_refuses_plain_marked_source(tmp_path):
    plain = _plain_stage(tmp_path)
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.98-draft", "January 1, 2027"],
                       cwd=REPO, capture_output=True, text=True,
                       env=dict(os.environ, SRC_DIR=str(plain), OUT_DIR=str(tmp_path / "out")))
    assert r.returncode != 0
    assert "plain-marked" in r.stderr, r.stderr
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.pdf"))


def test_the_standalone_builder_refuses_plain_marked_source_and_builds_without_the_label(tmp_path):
    """NEGATIVE CONTROL: the same tree, label removed, builds -- so the refusal
    is the label's doing and not some other failure."""
    plain = _plain_stage(tmp_path)
    env = dict(os.environ, SRC_DIR=str(plain), OUT_DIR=str(tmp_path / "out"))
    cmd = ["bash", "build/build-standalone.sh", "7", "v0.98-draft"]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)
    assert r.returncode != 0
    assert "plain-marked" in r.stderr, r.stderr
    (plain / SENTINEL).unlink()
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)
    assert "plain-marked" not in r.stderr, r.stderr
    assert r.returncode == 0, r.stderr[-500:]
