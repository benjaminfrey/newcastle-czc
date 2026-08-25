"""The old-side resolver for a baseline redline.

The bug this prevents: build-redline-full.sh's loop writes an EMPTY old-side
when `git show <old>:source/<same-name>` fails, so a renamed article renders as
100% new with only a console note. Against v0.1-baseline that is 8 of 9 files.

It also prevents a second, subtler failure: diffing an article whose content
moved out of markdown into a native-Typst unit (Article 2's district
standards) would report thousands of phantom deletions. That case must exit 4
and be rendered UNMARKED by the caller, never diffed.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RESOLVE = REPO / "build" / "redline_resolve.py"
REDLINE_TEXT = REPO / "build" / "redline-text.py"


def run(*args):
    return subprocess.run([sys.executable, str(RESOLVE), *args],
                          capture_output=True, text=True, cwd=REPO)


def test_a_renamed_article_resolves_to_real_baseline_content(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    assert len(text) > 1000, "should contain the baseline Administration article"
    assert "ADMINISTRATION" in text.upper()


def test_article_3_reports_new_rather_than_empty_silence(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-03-streets-roads-driveways.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 3, "new-at-adoption must be its own exit code"
    assert "new at this adoption" in (r.stdout + r.stderr).lower()


def test_an_unmapped_article_fails_loudly(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-99-invented.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode not in (0, 3), "an unmapped file must not succeed"
    assert "adoption-map.json" in (r.stdout + r.stderr)


def test_without_baseline_flag_it_uses_the_same_filename(tmp_path):
    """Draft-to-draft redlines keep today's behaviour untouched."""
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.23-draft", str(out))
    assert r.returncode == 0, r.stderr
    assert len(out.read_text()) > 1000


def test_article_2_prefatory_is_not_text_comparable(tmp_path):
    """AMENDED 2026-08-24 (spec §1.2b): Article 2's district standards moved
    to article-02.typ. This article must exit 4, not be resolved and diffed
    like a normal renamed file, even though it does have a mapped baseline
    counterpart (article-02-districts.md) in adoption-map.json."""
    out = tmp_path / "old.md"
    r = run("article-02-prefatory.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 4, r.stdout + r.stderr
    msg = (r.stdout + r.stderr).lower()
    assert "not text-comparable" in msg
    assert not out.exists() or out.read_text() == "", \
        "exit 4 must not write a diffable old side; the caller supplies old==new"


def _count_indented_lines(text: str) -> int:
    return sum(1 for ln in text.split("\n") if ln[:1] in (" ", "\t") and ln.strip())


def test_a_real_baseline_run_preserves_administrations_indented_sub_clauses(tmp_path):
    """THE regression for the 2026-08-24 review finding: resolving
    article-08-administration.md against the real v0.1-baseline must not
    flatten its lettered sub-clauses (a., b., c. ...) the way feeding
    normalize()'s rewrap rule to the renderer did -- that measured as 211
    indented lines collapsing to 4. redline_resolve.py must use
    normalize_old_side, which preserves indentation, so the resolved old side
    has exactly as many indented lines as the raw baseline text it came from.
    """
    raw_baseline = subprocess.run(
        ["git", "-C", str(REPO), "show", "v0.1-baseline:source/article-07-administration.md"],
        capture_output=True, text=True,
    ).stdout
    expected = _count_indented_lines(raw_baseline)
    assert expected > 100, "sanity check: the baseline article has this many sub-clauses"

    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 0, r.stderr
    assert _count_indented_lines(out.read_text()) == expected


def test_not_text_comparable_article_renders_with_no_marks(tmp_path):
    """The exit-4 caller contract, exercised directly: when the caller honours
    it (old side = new side), redline-text.py --source must mark nothing --
    no struck deletions, no red insertions -- for this article."""
    current = (REPO / "source" / "article-02-prefatory.md").read_text()
    old = tmp_path / "old.md"
    new = tmp_path / "new.md"
    out = tmp_path / "out.md"
    old.write_text(current)
    new.write_text(current)

    r = subprocess.run(
        [sys.executable, str(REDLINE_TEXT), str(old), str(new), str(out), "--source"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 0, r.stderr
    rendered = out.read_text()
    assert "~~" not in rendered, "no struck (deleted) text should appear"
    assert "cc0000" not in rendered, "no red (added) text should appear"
    assert rendered.strip() == current.strip()
