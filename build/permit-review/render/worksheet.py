"""Implements CONTRACT.md §6.3 (POST /api/worksheet/render) and §2's named
home `render/worksheet.py` for `render_worksheet(payload, out_dir) -> Path`.

Assembles the Phase-1 dimensional worksheet -- Required Review(s),
Dimensional Standards, Permitted Buildings, and the verbatim Use/Design/
District Standards panels (CONTRACT.md §6.2) -- as a `render.findings_to_md`
node list, renders it to markdown, and shells out to
`render/build-findings.sh` (pandoc -> Typst -> PDF via
`style/findings-template.typ`) to produce the PDF.

FRAMING RULE, restated: this is THE WORKSHEET, not a decision. Every row
prints the Code's own text, a blank "Proposed" slot, and its citation. No
conclusion is rendered anywhere (CONTRACT.md preamble, §6.2). Citation text
comes ONLY from app.citation.render() (CONTRACT.md §5.1) -- this module never
hand-builds a citation string.

Reads only the committed, already-built rulesets/<ruleset_key>/*.json (never
repo source directly -- CONTRACT.md §4 preamble: "Runtime never re-parses
repo source"). Prefers app.rulesets.load_ruleset() (the canonical loader,
which also owns the binding gate machinery) and falls back to reading the
files directly if app.rulesets is unavailable, mirroring app/main.py's own
degrade-gracefully pattern for the same reason.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import citation  # noqa: E402
from render.findings_to_md import (  # noqa: E402
    boardq,
    finding,
    heading,
    kv,
    para,
    render_nodes,
    rule,
    table,
)

BUILD_SCRIPT = Path(__file__).resolve().parent / "build-findings.sh"


class WorksheetRenderError(RuntimeError):
    """Raised when the worksheet cannot be assembled or rendered -- an
    unknown district/use, a missing ruleset, or a build-findings.sh failure.
    Distinct from validation errors, which app/main.py's route already
    rejects with 400 before ever calling render_worksheet()."""


# --------------------------------------------------------------------------- #
# Ruleset access -- prefers app.rulesets, falls back to reading files
# directly. Same reasoning as app/main.py's own fallback (CONTRACT.md §4).
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_ruleset(ruleset_key: str) -> dict[str, Any]:
    try:
        from app import rulesets as rulesets_mod

        rs = rulesets_mod.load_ruleset(ruleset_key)
        return {
            "manifest": rs.manifest,
            "districts_by_key": rs.districts_by_key,
            "uses_by_key": rs.uses_by_key,
            "cells_by_pair": rs.cells_by_pair,
        }
    except Exception:  # noqa: BLE001 -- fall back to the direct file read below
        pass

    from app.config import RULESETS_DIR

    base = RULESETS_DIR / ruleset_key
    districts_path = base / "districts.json"
    use_matrix_path = base / "use-matrix.json"
    manifest_path = base / "manifest.json"
    if not (districts_path.exists() and use_matrix_path.exists()):
        raise WorksheetRenderError(
            f"ruleset {ruleset_key!r} is not built (missing districts.json/use-matrix.json "
            f"under {base})"
        )
    districts = _read_json(districts_path)
    use_matrix = _read_json(use_matrix_path)
    manifest = _read_json(manifest_path) if manifest_path.exists() else {"binding": False}
    return {
        "manifest": manifest,
        "districts_by_key": {d["district_key"]: d for d in districts["districts"]},
        "uses_by_key": {u["use_key"]: u for u in use_matrix["uses"]},
        "cells_by_pair": {(c["district_key"], c["use_key"]): c for c in use_matrix["cells"]},
    }


# --------------------------------------------------------------------------- #
# Node assembly -- CONTRACT.md §6.2's four worksheet sections.
# --------------------------------------------------------------------------- #


def _required_review_nodes(idx: dict[str, Any], district: dict[str, Any], use_keys: list[str]) -> list[dict]:
    nodes: list[dict] = [heading("Required Review(s)", level=3)]
    use_objs = [idx["uses_by_key"][k] for k in use_keys] if use_keys else idx["uses_by_key"].values()
    rows: list[list[str]] = []
    for use_obj in use_objs:
        cell = idx["cells_by_pair"].get((district["district_key"], use_obj["use_key"]))
        if cell is None:
            continue
        row = citation.required_review_row(district, use_obj, cell)
        cite_text = citation.render(row["citation"], style="short")
        rows.append([
            use_obj["label"],
            row["permit"] or "(none — prohibited)",
            row["authority"] or "—",
            row["sentence"],
            cite_text,
        ])
    if rows:
        nodes.append(table(["Use", "Permit", "Authority", "Applicability", "Citation"], rows))
    else:
        nodes.append(para("_No use selected — the full 63-use table is omitted from this excerpt._"))
    return nodes


def _dimensional_standards_nodes(ruleset_key: str, district: dict[str, Any]) -> list[dict]:
    nodes: list[dict] = [heading("Dimensional Standards", level=3)]
    dims = district.get("dimensions", [])
    if not dims:
        nodes.append(para("_Article 2 establishes no dimensional panels for this District._"))
        return nodes
    rows: list[list[str]] = []
    unresolved_notes: list[str] = []
    for dim in dims:
        cite = citation.render(citation.from_dimension(ruleset_key, district, dim))
        if dim.get("applicability") == "not_established":
            required = "Article 2 establishes no standard for this field."
        else:
            required = dim.get("raw", "")
        marker = "".join(f"({r})" for r in dim.get("footnote_refs", []))
        label = f"{dim.get('label', '')} {marker}".strip()
        rows.append([label, required, "______", cite])
        if dim.get("unresolved"):
            for note in dim.get("notes", []):
                unresolved_notes.append(f"{dim.get('label', '')}: {note}")
    nodes.append(table(["Label", "Required (from the Code)", "Proposed", "Citation"], rows))
    for note in unresolved_notes:
        nodes.append(boardq(note))
    return nodes


def _permitted_buildings_nodes(district: dict[str, Any]) -> list[dict]:
    nodes: list[dict] = [heading("Permitted Buildings", level=3)]
    matrix = district.get("building_matrix")
    absent = district.get("building_matrix_absent")
    if matrix:
        header = ["Standard", *matrix.get("cols", [])]
        rows = [[str(v) for v in row] for row in matrix.get("rows", [])]
        nodes.append(table(header, rows))
    elif absent:
        nodes.append(finding(absent.get("finding", "")))
        if absent.get("board_question"):
            nodes.append(boardq(absent["board_question"]))
    else:
        nodes.append(para("_No Permitted Buildings matrix on record for this District._"))
    return nodes


def _panel_nodes(district: dict[str, Any]) -> list[dict]:
    nodes: list[dict] = []
    use_standards = district.get("use_standards")
    if use_standards and use_standards.get("items"):
        nodes.append(heading(use_standards.get("title", "Use Standards"), level=3))
        for item in use_standards["items"]:
            text = item.get("text") if isinstance(item, dict) else item
            if text:
                nodes.append(para(f"- {text}"))
    for panel in district.get("panels", []):
        kind = panel.get("kind")
        body = panel.get("body")
        nodes.append(heading(str(panel.get("title", "")), level=3))
        if kind == "para":
            nodes.append(para(str(body)))
        elif kind == "lv":
            nodes.append(kv([(p[0], p[1]) for p in (body or [])]))
        elif kind == "list":
            for entry in body or []:
                text = entry.get("text") if isinstance(entry, dict) else entry
                if text:
                    nodes.append(para(f"- {text}"))
    return nodes


def build_worksheet_nodes(payload: dict[str, Any]) -> tuple[list[dict], list[dict[str, Any]]]:
    """Returns (nodes, unresolved_inventory) for one worksheet render.

    `unresolved_inventory` is the honest-blanks list CONTRACT.md §6.3 asks
    the /api/worksheet/render response to carry back as `unresolved[]`.
    """
    ruleset_key = payload["ruleset_key"]
    district_key = payload["district_key"]
    use_keys = list(payload.get("use_keys") or [])

    idx = _load_ruleset(ruleset_key)
    district = idx["districts_by_key"].get(district_key)
    if district is None:
        raise WorksheetRenderError(f"unknown district {district_key!r} in ruleset {ruleset_key!r}")
    for u in use_keys:
        if u not in idx["uses_by_key"]:
            raise WorksheetRenderError(f"unknown use {u!r} in ruleset {ruleset_key!r}")

    case_label = payload.get("case_label") or ""
    meeting_date = payload.get("meeting_date")
    draft_due = payload.get("draft_due")
    lots = payload.get("lots") or []
    notes = payload.get("notes") or ""
    scratch = bool(payload.get("scratch", False))

    nodes: list[dict] = [
        heading("Dimensional Worksheet", level=1),
        kv([
            ("District", district.get("display_name", district.get("code"))),
            ("Case", case_label or "(unlabeled)"),
            ("Meeting date", meeting_date or "(next regular meeting)"),
            ("Draft due", draft_due or ""),
            ("Ruleset", f"{ruleset_key}" + (" — SCRATCH / NON-BINDING DRY RUN" if scratch else "")),
        ]),
    ]
    if scratch or not idx["manifest"].get("binding"):
        nodes.append(
            boardq(
                "This worksheet was rendered against a NON-BINDING ruleset "
                f"({ruleset_key!r}) and MUST NOT be relied on for a real case."
            )
        )
    if lots:
        nodes.append(heading("Lots", level=4))
        nodes.append(table(["Label"], [[str(lot.get("label", lot)) if isinstance(lot, dict) else str(lot)] for lot in lots]))
    if notes:
        nodes.append(heading("Notes", level=4))
        nodes.append(para(notes))
    nodes.append(rule())

    nodes += _required_review_nodes(idx, district, use_keys)
    nodes += _dimensional_standards_nodes(ruleset_key, district)
    nodes += _permitted_buildings_nodes(district)
    nodes += _panel_nodes(district)

    unresolved: list[dict[str, Any]] = []
    for dim in district.get("dimensions", []):
        if dim.get("unresolved"):
            unresolved.append({
                "kind": "dimension",
                "field_key": dim.get("field_key"),
                "label": dim.get("label"),
                "notes": dim.get("notes", []),
            })
    if district.get("building_matrix_absent"):
        unresolved.append({"kind": "building_matrix_absent", **district["building_matrix_absent"]})

    return nodes, unresolved


# --------------------------------------------------------------------------- #
# render_worksheet() -- the CONTRACT.md-named entry point.
# --------------------------------------------------------------------------- #


def render_worksheet(payload: dict[str, Any], out_dir: Path) -> Path:
    """Build + render one worksheet PDF into `out_dir` (always
    data/exports/, enforced by the caller -- app/main.py -- per CONTRACT.md
    §1 S5/§6.3/§8.6). Returns the written PDF's path.

    Filename: `<YYYYMMDD-HHMMSS>-<district_key>-worksheet.pdf` (CONTRACT.md
    §6.3).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes, _unresolved = build_worksheet_nodes(payload)
    md_text = render_nodes(nodes)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    district_key = payload["district_key"]
    pdf_name = f"{stamp}-{district_key}-worksheet.pdf"
    pdf_path = out_dir / pdf_name

    md_path = out_dir / f".{stamp}-{district_key}-worksheet.md.tmp"
    md_path.write_text(md_text, encoding="utf-8")

    meeting_date = payload.get("meeting_date") or ""
    caption = payload.get("case_label") or ""
    running_head = "Dimensional Worksheet"

    try:
        proc = subprocess.run(
            [
                "bash",
                str(BUILD_SCRIPT),
                str(md_path),
                str(pdf_path),
                meeting_date,
                caption,
                running_head,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        md_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise WorksheetRenderError(
            f"build-findings.sh failed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise WorksheetRenderError(f"build-findings.sh reported success but {pdf_path} is missing/empty")

    return pdf_path
