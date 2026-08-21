"""End-to-end proof of the render pipeline: build a node list, render it to
markdown via findings_to_md.render_nodes(), then shell out to
render/build-findings.sh to produce a real PDF.

CONTRACT.md scope note: this workflow (Phase 0/1) has NO uploads, NO OCR and
NO LLM, so this script cannot draw on a real application. Every fact below is
FABRICATED SAMPLE DATA for a parcel and applicant that do not exist — never a
real Newcastle case, and never a real Board member's name — chosen precisely
so this can be run and its output shared without touching PII. It exists to
prove three things work together: (1) app/citation.py's Citation struct is
the only source of citation text (CONTRACT.md §5.1), rendered here through
the real module, not hand-typed; (2) findings_to_md.py's raw_attribute
mechanism reaches every one of style/findings-template.typ's eight helpers;
(3) render/build-findings.sh actually produces a paginated PDF with a working
running head, footer and DRAFT watermark.

Usage:
    cd build/permit-review
    python3 render/demo_findings.py
    # -> data/exports/<timestamp>-sample-findings.pdf
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import meetings  # noqa: E402
from app.citation import Citation, render as render_citation  # noqa: E402
from render.findings_to_md import (  # noqa: E402
    boardq,
    conditions,
    finding,
    heading,
    kv,
    motionblock,
    para,
    render_nodes,
    rule,
    signaturegrid,
    standard,
    table,
    unresolved,
)

SAMPLE_CASE_LABEL = "SAMPLE — Map 000, Lot 000 (Demo Parcel, fictional)"


def build_demo_nodes() -> list[dict]:
    """Assemble a small but representative Findings of Fact & Conclusions of
    Law draft, exercising every node type findings_to_md.py understands."""

    frontage_citation = Citation(
        ruleset_key="adopted",
        scheme="adopted",
        article=2,
        district_code="D1",
        district_name="Rural",
        panel_title="LOT DIMENSIONS",
        label="Primary Frontage Line Length",
    )
    frontage_citation_text = render_citation(frontage_citation, style="short")

    nodes: list[dict] = [
        heading("Findings of Fact and Conclusions of Law", level=1),
        para(
            "*for the fictional sample application submitted by* "
            "**Jordan A. Sample** *for* **Map 000, Lot 000 (Demo Parcel)** — "
            "**this is demonstration output, not a real case.**"
        ),
        rule(),
        heading("Findings of Fact", level=1),
        heading("Project Information", level=3),
        kv([
            ("Applicant", "Jordan A. Sample (fictional demo applicant)"),
            ("Property Owner", "Jordan A. Sample"),
            ("Tax Lot", "Map 000, Lot 000"),
            ("Core Zoning District", "D1 - Rural"),
            ("Existing Use", "Undeveloped"),
            ("Proposed Development", "Construction of one residential building"),
        ]),
        heading("Required Review(s)", level=3),
        table(
            ["Required Review", "Permitting Authority", "Applicability"],
            [
                ["Use Permit", "CEO",
                 "A Residence use in the D1-Rural District requires a Use "
                 "Permit which can be issued by the CEO."],
                ["Small Project Plan", "CEO",
                 "The Permitting Authority for Residential buildings in the "
                 "D1-Rural District is the CEO."],
            ],
        ),
        heading("Standards for Review", level=2),
        heading("D1 - Rural", level=3),
        standard(
            "Primary Frontage Line Length (min) Required: 250 ft.",
            citation=frontage_citation_text,
        ),
        unresolved(
            "Proposed frontage: ______ (no application has been uploaded in "
            "this phase of the app — Phase 1 ships no ingest step, so this "
            "field is blank by design, not by omission)."
        ),
        boardq(
            "Does the record before the Board establish the parcel's actual "
            "road frontage, or is a survey needed before this standard can "
            "be evaluated?"
        ),
        rule(),
        heading("Conclusions of Law", level=1),
        para(
            "Based on the facts above, the Newcastle Planning Board must "
            "reach its own conclusions of law. This draft states none on the "
            "Board's behalf; each item below is a question for the Board, "
            "not an answer supplied by this app."
        ),
        boardq(
            "Is the proposed development, as described in the record, in "
            "conformance with Article 2 of the Core Zoning Code?"
        ),
        rule(),
        heading("Decision of the Planning Board", level=1),
        motionblock(),  # every field left none -> every slot renders blank
        heading("Conditions of Approval", level=3),
        conditions([]),  # empty -> one genuinely blank numbered slot
        heading("Signatures", level=3),
        signaturegrid([
            {"name": "Sample Signer A", "title": "Chair"},
            {"name": "Sample Signer B", "title": "Vice Chair"},
            {"name": "Sample Signer C"},
            {"name": "Sample Signer D"},
            {"name": "Sample Signer E"},
            {"name": "Sample Signer F"},
        ]),
    ]
    return nodes


def main() -> int:
    nodes = build_demo_nodes()
    markdown = render_nodes(nodes)

    tmp_dir = APP_ROOT / "data" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    md_path = tmp_dir / "demo-findings.md"
    md_path.write_text(markdown, encoding="utf-8")

    exports_dir = APP_ROOT / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    out_path = exports_dir / f"{stamp}-sample-findings.pdf"

    meeting_dt = meetings.next_meeting_date()
    meeting_str = meeting_dt.strftime("%B %-d, %Y")
    draft_due = meetings.draft_due_date(meeting_dt).strftime("%B %-d, %Y")

    build_script = Path(__file__).resolve().parent / "build-findings.sh"
    result = subprocess.run(
        [
            "bash", str(build_script),
            str(md_path), str(out_path),
            meeting_str, SAMPLE_CASE_LABEL,
        ],
        env={
            **__import__("os").environ,
            "DRAFT": "1",
            "PROVENANCE": "1",
        },
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        print(f"build-findings.sh failed (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    print(f"Meeting date: {meeting_str}  ·  Draft due: {draft_due}")
    print(f"Sample findings PDF: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
