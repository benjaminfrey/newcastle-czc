"""build/release_gate.py -- refuses an incomplete or mis-paginated release.

PDFs are synthetic (PyMuPDF), with the footer the real builds print.
"""
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import release_gate  # noqa: E402

VER = "v0.98-draft"


def make_pdf(path, numbers, footer="Newcastle Core Zoning Code | {n}"):
    """One page per entry; None = a page with no printed number."""
    d = pymupdf.open()
    for n in numbers:
        p = d.new_page(width=612, height=792)
        p.insert_text((72, 100), "body text 12")
        if n is not None:
            p.insert_text((72, 770), footer.format(n=n))
    d.save(str(path))
    d.close()
    return path


def plan(*files):
    return {"version": VER, "artifacts": [{"kind": "k", "article": None, "files": list(files)}]}


def run_cli(plan_dict, d, tmp_path):
    pj = tmp_path / "plan.json"
    pj.write_text(json.dumps(plan_dict))
    return subprocess.run([sys.executable, str(BUILD / "release_gate.py"), str(pj), str(d)],
                          capture_output=True, text=True)


@pytest.fixture
def rel(tmp_path):
    d = tmp_path / "rel"
    d.mkdir()
    make_pdf(d / "a.pdf", [1, 2, 3])
    (d / "a.md").write_text("text\n")
    return d


def test_complete_set_passes(rel, tmp_path):
    p = plan("a.pdf", "a.md")
    assert release_gate.check(p, rel) == []
    r = run_cli(p, rel, tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "release_gate: 2 file(s) checked"


def test_missing_planned_file(rel):
    probs = release_gate.check(plan("a.pdf", "a.md", "gone.md"), rel)
    assert len(probs) == 1 and "gone.md" in probs[0]


def test_zero_byte_file(rel):
    (rel / "a.md").write_text("")
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "a.md" in probs[0]


def test_gap_in_numbers_is_refused(rel):
    make_pdf(rel / "a.pdf", [1, 2, 4])
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "a.pdf" in probs[0]


def test_unnumbered_front_matter_then_constant_offset_passes(rel):
    make_pdf(rel / "a.pdf", [None, None, 1, 2, 3])
    assert release_gate.check(plan("a.pdf", "a.md"), rel) == []


def test_no_printed_number_is_refused(rel):
    make_pdf(rel / "a.pdf", [None, None])
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "a.pdf" in probs[0]


def test_reversed_footer_form_is_read(rel):
    make_pdf(rel / "a.pdf", [1, 2], footer="{n} | Newcastle Core Zoning Code")
    assert release_gate.footer_numbers(rel / "a.pdf") == [(1, 1), (2, 2)]
    assert release_gate.check(plan("a.pdf", "a.md"), rel) == []


def test_body_numbers_outside_the_band_are_ignored(rel):
    # body text carries "12"; only the footer band counts
    assert release_gate.footer_numbers(rel / "a.pdf") == [(1, 1), (2, 2), (3, 3)]


def test_unplanned_file_is_refused(rel):
    (rel / "stray.txt").write_text("x")
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "stray.txt" in probs[0]


def test_existing_summary_pdf_is_allowed(rel):
    (rel / f"Summary of Changes {VER}.pdf").write_bytes(b"%PDF-1.4 x")
    assert release_gate.check(plan("a.pdf", "a.md"), rel) == []


def test_hidden_files_are_refused(rel):
    (rel / ".DS_Store").write_text("x")
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and ".DS_Store" in probs[0] and "not in the release plan" in probs[0]


def test_unopenable_pdf_is_a_problem_not_a_traceback(rel):
    (rel / "a.pdf").write_bytes(b"not a pdf at all")
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "a.pdf" in probs[0]


def test_cli_lists_every_problem(rel, tmp_path):
    make_pdf(rel / "a.pdf", [1, 3])
    (rel / "stray.txt").write_text("x")
    r = run_cli(plan("a.pdf", "a.md", "gone.md"), rel, tmp_path)
    assert r.returncode == 1
    lines = r.stderr.strip().splitlines()
    assert len(lines) == 3 and all(l.startswith("release_gate: ") for l in lines)
    assert r.stdout == ""


def test_odd_constant_offset_is_refused(rel):
    make_pdf(rel / "a.pdf", [None, 1, 2])  # numbered from physical page 2: offset -1
    probs = release_gate.check(plan("a.pdf", "a.md"), rel)
    assert len(probs) == 1 and "a.pdf" in probs[0] and "-1" in probs[0]


@pytest.mark.parametrize("name", ["../outside.md", "sub/a.md", "sub\\a.md", ".", ".."])
def test_planned_name_must_be_a_bare_filename(rel, tmp_path, name):
    (tmp_path / "outside.md").write_text("x")
    probs = release_gate.check(plan("a.pdf", name), rel)
    assert any(name in p for p in probs)


def test_planned_symlink_is_refused(rel, tmp_path):
    other = make_pdf(tmp_path / "other.pdf", [1, 2])
    (rel / "x.pdf").symlink_to(other)
    probs = release_gate.check(plan("a.pdf", "x.pdf"), rel)
    assert any("x.pdf" in p and "symlink" in p for p in probs)


@pytest.mark.parametrize("bad", [
    {"artifacts": []},
    {"version": VER, "artifacts": "nope"},
    {"version": VER, "artifacts": [{"kind": "k"}]},
    {"version": VER, "artifacts": [{"files": "a.pdf"}]},
    {"version": VER, "artifacts": [5]},
    [],
])
def test_malformed_plan_is_a_problem(rel, bad):
    probs = release_gate.check(bad, rel)
    assert probs and all(isinstance(p, str) for p in probs)


def test_unreadable_plan_json_is_a_cli_refusal(rel, tmp_path):
    pj = tmp_path / "plan.json"
    pj.write_text("{not json")
    r = subprocess.run([sys.executable, str(BUILD / "release_gate.py"), str(pj), str(rel)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and r.stderr.startswith("release_gate: ")
    assert "Traceback" not in r.stderr


def test_duplicate_planned_file_is_a_problem(rel):
    probs = release_gate.check(plan("a.pdf", "a.md", "a.md"), rel)
    assert len(probs) == 1 and "a.md" in probs[0] and "twice" in probs[0]


REPO = BUILD.parent


def kind_plan(kind, *files):
    return {"version": VER, "artifacts": [{"kind": kind, "article": None, "files": list(files)}]}


@pytest.fixture
def memo(tmp_path):
    d = tmp_path / "memo"
    d.mkdir()
    (d / "m.md").write_text("# Use Table Changes\n\nOne use moved.\n\nAnother line.\n")
    out = tmp_path / "rel2"
    out.mkdir()
    r = subprocess.run(["bash", str(BUILD / "build-memo.sh"), str(d / "m.md"), str(out / "m.pdf"),
                        f"Use Table Changes — {VER}",
                        "Newcastle Core Zoning Code · January 1, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out


def test_real_memo_passes_under_use_table_changes(memo):
    assert release_gate.check(kind_plan("use-table-changes", "m.pdf"), memo) == []


def test_real_memo_refused_under_a_code_kind(memo):
    probs = release_gate.check(kind_plan("standalone", "m.pdf"), memo)
    assert len(probs) == 1 and "m.pdf" in probs[0]


def test_unknown_kind_gets_the_strict_rules(memo):
    assert release_gate.check(kind_plan("mystery", "m.pdf"), memo)


def test_textless_pdf_refused_under_use_table_changes(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(str(d / "m.pdf"))
    pdf.close()
    probs = release_gate.check(kind_plan("use-table-changes", "m.pdf"), d)
    assert len(probs) == 1 and "m.pdf" in probs[0]


@pytest.mark.parametrize("kind", [["x"], {"a": 1}, 3, None, "MISSING"])
def test_bad_artifact_kind_is_a_refusal_not_a_traceback(rel, tmp_path, kind):
    art = {"files": ["a.pdf", "a.md"]}
    if kind != "MISSING":
        art["kind"] = kind
    p = {"version": VER, "artifacts": [art]}
    probs = release_gate.check(p, rel)
    assert probs and any("kind" in x for x in probs)
    r = run_cli(p, rel, tmp_path)
    assert r.returncode == 1 and "release_gate: " in r.stderr
    assert "Traceback" not in r.stderr
