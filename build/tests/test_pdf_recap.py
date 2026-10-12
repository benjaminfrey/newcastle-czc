"""pdf_recap reports every PDF, and fails on one it cannot read."""
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent


def _run(*args):
    return subprocess.run([sys.executable, "build/pdf_recap.py", *args],
                          cwd=REPO, capture_output=True, text=True)


def _pdf(path, pages=1):
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page().insert_text((72, 72), "hello")
    doc.save(str(path))
    doc.close()
    return path


def test_good_pdf_exits_zero_and_prints_its_line(tmp_path):
    good = _pdf(tmp_path / "good.pdf", 2)
    r = _run(f"Good={good}")
    assert r.returncode == 0, r.stderr
    assert "Good" in r.stdout and "2 pages, 0 blank" in r.stdout


def test_blank_pages_are_a_report_not_a_failure(tmp_path):
    doc = pymupdf.open()
    doc.new_page()
    p = tmp_path / "blank.pdf"
    doc.save(str(p))
    r = _run(f"Blank={p}")
    assert r.returncode == 0
    assert "1 pages, 1 blank" in r.stdout


def test_unopenable_file_fails_after_printing_every_line(tmp_path):
    good = _pdf(tmp_path / "good.pdf")
    junk = tmp_path / "junk.pdf"
    junk.write_text("not a pdf")
    r = _run(f"Junk={junk}", f"Missing={tmp_path / 'nope.pdf'}", f"Good={good}")
    assert r.returncode == 1
    assert "Junk" in r.stdout and "Missing" in r.stdout
    assert "1 pages, 0 blank" in r.stdout  # the line after the failures still printed


def test_zero_page_pdf_fails(tmp_path):
    # PyMuPDF refuses to save a zero-page document, so hand-write one.
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R/Size 3>>\n%%EOF\n")
    r = _run(f"Empty={empty}")
    assert r.returncode == 1
    assert "Empty" in r.stdout
