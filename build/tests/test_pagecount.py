"""czc_pagecount (build/pagecount.sh) must yield a bare integer or fail loudly.

Its output feeds shell arithmetic (OFFSET=$((OFFSET + PAGES))) and a Typst
--input, and OFFSET is what every Article's verso/recto chrome is keyed to.
Newer PyMuPDF prints a deprecation notice to STDOUT for `import fitz`; captured
by $(...) it became part of the "number", and under `set -u` bash reported its
first word as "line N: warning: unbound variable". That broke every PDF-building
test on CI while passing on a machine with an older PyMuPDF.
"""
import os
import re
import subprocess
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parents[2]
SOURCES = [p for p in (REPO / "build").rglob("*")
           if p.suffix in {".py", ".sh"}
           and not {".venv", "__pycache__", "permit-review", "tests"} & set(p.parts)]


def _pdf(tmp_path, pages=3):
    pdf = tmp_path / "x.pdf"
    d = pymupdf.open()
    for _ in range(pages):
        d.new_page()
    d.save(pdf)
    d.close()
    return pdf


def _run(tmp_path, pdf, *, path_prefix=None):
    e = dict(os.environ)
    if path_prefix:
        e["PATH"] = f"{path_prefix}{os.pathsep}{e['PATH']}"
    return subprocess.run(
        ["bash", "-c", 'set -euo pipefail; source build/pagecount.sh; czc_pagecount "$1"', "_", str(pdf)],
        cwd=REPO, env=e, capture_output=True, text=True)


def test_prints_the_bare_integer(tmp_path):
    r = _run(tmp_path, _pdf(tmp_path, 3))
    assert r.returncode == 0, r.stderr
    assert r.stdout == "3\n"


def test_stdout_noise_fails_loudly_instead_of_becoming_the_page_count(tmp_path):
    # A python3 that, like PyMuPDF with `import fitz`, prints a notice on stdout.
    shim = tmp_path / "bin"
    shim.mkdir()
    (shim / "python3").write_text(
        '#!/bin/sh\nprintf "warning: The fitz API is deprecated\\n3\\n"\n')
    (shim / "python3").chmod(0o755)
    r = _run(tmp_path, _pdf(tmp_path), path_prefix=str(shim))
    assert r.returncode != 0
    assert "czc_pagecount" in r.stderr and "deprecated" in r.stderr
    assert r.stdout == ""


def test_build_code_imports_pymupdf_not_the_deprecated_fitz():
    # `import fitz` is deprecated and, in current PyMuPDF, writes to stdout.
    pat = re.compile(r"^\s*(import|from)\s+fitz\b|import\s+sys,\s*fitz\b", re.M)
    offenders = [str(p.relative_to(REPO)) for p in SOURCES
                 if pat.search(p.read_text(errors="replace"))]
    assert not offenders, f"use `pymupdf`, not the deprecated `fitz`: {offenders}"
