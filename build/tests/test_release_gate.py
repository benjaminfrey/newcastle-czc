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


def test_hidden_files_ignored(rel):
    (rel / ".DS_Store").write_text("x")
    assert release_gate.check(plan("a.pdf", "a.md"), rel) == []


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
