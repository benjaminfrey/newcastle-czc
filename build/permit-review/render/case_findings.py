"""Implements CONTRACT.md §10 (the findings render mapping) and the W6 task
brief's item 5, "the draft document": Node tree -> markdown ->
render/build-findings.sh -> style/findings-template.typ -> PDF in
data/exports/.

THE FRAMING RULE, restated (CONTRACT.md preamble): this module renders THE
WORKING DRAFT THE BOARD AMENDS, never a decision. It never writes a
conclusion (the DB schema structurally prevents that -- `findings_nodes.
conclusion` is only ever set by a human, CONTRACT.md §3.6), and every node
this module cannot fill honestly renders as a highlighted blank
(`#unresolved`/`#boardq`) rather than being silently omitted. A case with
few or no extracted facts still produces a COMPLETE walk of its findings
tree -- every standard quoted, every finding blank and flagged -- never a
short, falsely-confident document.

WHAT THIS MODULE DOES AND DOES NOT DO. It reads three kinds of already-
durable state -- the `cases` row, the CURRENT (superseded_by IS NULL)
`findings_nodes` tree, and the `motions`/`conditions`/`board_members`
tables -- and turns them into the `render.findings_to_md` node list that
`render/build-findings.sh` already knows how to render (verified end to end
by tests/test_render.py). It builds NOTHING that isn't already in the
database: it does not decide applicability, does not run the deterministic
engine, and does not draft prose. Those are engine/'s job (W6 items 1-4);
this module is purely the last mile from a findings tree to a PDF, exactly
the same split `render/worksheet.py` already has from a built ruleset to a
PDF.

READ docs/Findings of Fact and Conclusions of Law/*.pdf BEFORE CHANGING THE
MAPPING BELOW. The two properties those real documents establish, in every
sample checked (Shattuck's adopted final, the Profenno/Uberoi DRAFTs):
  (1) the quoted standard is flush left; the Board's finding beneath it is
      indented and italic -- exactly style/findings-template.typ's
      #standard/#finding pair, already built and already tested;
  (2) a document with no meeting held yet (a DRAFT) carries exactly ONE
      Decision-of-the-Board block near the end, every field genuinely
      blank (Moved by/Second/Result print as a highlighted "..."), one
      genuinely blank numbered condition slot, and blank signature lines --
      never a fabricated vote. This module reproduces that: when the
      `motions` table has no rows yet for a case (the normal state before
      W7's meeting workflow exists), it emits exactly one blank
      `motionblock()`, not one per criterion.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import citation as citation_mod  # noqa: E402
from render.findings_to_md import (  # noqa: E402
    boardq,
    conditions as conditions_node,
    finding,
    heading,
    kv,
    md_escape,
    motionblock,
    para,
    render_nodes,
    rule,
    signaturegrid,
    standard,
    unresolved,
)

BUILD_SCRIPT = Path(__file__).resolve().parent / "build-findings.sh"

# The fields app.citation.Citation actually declares -- used to filter a
# stored citation_json dict down to only the keys Citation() accepts, so an
# engine that stores one extra key some day can't crash rendering (CONTRACT.md
# §5.1: citation text is only ever produced by app/citation.py, never
# hand-built here; this is purely a defensive deserialization boundary).
_CITATION_FIELDS = (
    "ruleset_key", "scheme", "article", "section", "subsection",
    "district_key", "district_code", "district_name", "panel_title", "label",
    "use_label", "exhibit", "table", "section_title", "standard_letter",
    "standard_title", "table_title",
)


class CaseNotFound(LookupError):
    """No `cases` row with the given id."""


class FindingsRenderError(RuntimeError):
    """The findings draft could not be assembled or rendered -- a missing
    case, or a build-findings.sh failure. Never raised for an ordinary
    honest blank; those render as #unresolved/#boardq, not an error."""


# --------------------------------------------------------------------------- #
# Small read helpers -- raw SQL, no ORM (CONTRACT.md §3.1).
# --------------------------------------------------------------------------- #


def _get_case_row(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if row is None:
        raise CaseNotFound(case_id)
    return row


def _get_ruleset_key(conn: sqlite3.Connection, ruleset_id: str) -> str:
    row = conn.execute("SELECT ruleset_key FROM rulesets WHERE id = ?;", (ruleset_id,)).fetchone()
    return row["ruleset_key"] if row is not None else "adopted"


def _citation_display(raw_json: str | None, *, default_ruleset_key: str, style: str = "short") -> str | None:
    """Deserialize a stored `citation_json` string into a Citation and render
    it -- the ONLY path any citation-shaped text reaches this document
    (CONTRACT.md §5.1). Never raises: a malformed/absent citation_json
    degrades to None (the node simply prints without a citation marker)
    rather than failing the whole render over one bad row.
    """
    if not raw_json:
        return None
    try:
        raw = json.loads(raw_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    filtered = {k: v for k, v in raw.items() if k in _CITATION_FIELDS}
    filtered.setdefault("ruleset_key", default_ruleset_key)
    filtered.setdefault("scheme", default_ruleset_key if default_ruleset_key in ("adopted", "draft") else "adopted")
    if "article" not in filtered:
        return None
    try:
        c = citation_mod.Citation(**filtered)
        if c.standard_letter:
            # RECONCILIATION FIX (W6 reconciliation pass): `render()` is
            # CONTRACT.md §5.1/§5.4's canonical, golden-locked path -- but
            # `app/citation.py`'s own Citation docstring documents
            # standard_letter/standard_title as "render_citation() only ...
            # NOT used by the original render()/§5.5 goldens". Left as a
            # plain render() call, a lettered Article 7 standard (exactly
            # the shape engine/criteria_seed.py seeds for all 21 subdivision
            # rules) silently loses its letter -- "Article 7, Section 12"
            # instead of "Article 7, Section 12, Standard n. (Flood Areas)",
            # the form both real subdivision decisions in docs/ actually
            # use (tests/test_subdivision_criteria_build.py's own goldens).
            # render_citation() reproduces that form; scheme=default_ruleset_key
            # is always a same-scheme (identity) conversion for a case's own
            # findings, so this can't raise NoCounterpart. Every other
            # citation shape (district panels, tables, exhibits) keeps using
            # render() unchanged below -- render_citation() does not
            # reproduce those forms and was never meant to.
            return citation_mod.render_citation(
                c, scheme=default_ruleset_key, style=style if style in ("long", "short") else "long"
            )
        return citation_mod.render(c, style=style)
    except Exception:  # noqa: BLE001 -- a malformed citation is a blank, never a crash
        return None


def _project_info_kv(case: sqlite3.Row) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if case["applicant_name"]:
        items.append(("Applicant", case["applicant_name"]))
    if case["map_lot"]:
        items.append(("Tax Lot", case["map_lot"]))
    if case["situs_address"]:
        items.append(("Project Address", case["situs_address"]))
    if case["district_key"]:
        items.append(("Core Zoning District", case["district_key"]))
    items.append(("Application Type", (case["application_type"] or "").replace("_", " ").title()))
    if case["case_number"]:
        items.append(("Case Number", case["case_number"]))
    return items


# --------------------------------------------------------------------------- #
# findings_nodes tree -> render nodes.
# --------------------------------------------------------------------------- #


def _load_findings_tree(conn: sqlite3.Connection, case_id: str) -> list[sqlite3.Row]:
    """The CURRENT tree only (CONTRACT.md §3.6: `WHERE superseded_by IS
    NULL`), ordered so a parent always precedes its children and siblings
    stay in `sort_order`."""
    rows = conn.execute(
        """
        SELECT * FROM findings_nodes
        WHERE case_id = ? AND superseded_by IS NULL
        ORDER BY sort_order;
        """,
        (case_id,),
    ).fetchall()

    by_parent: dict[str | None, list[sqlite3.Row]] = {}
    for r in rows:
        by_parent.setdefault(r["parent_id"], []).append(r)

    ordered: list[tuple[int, sqlite3.Row]] = []

    def _walk(parent_id: str | None, depth: int) -> None:
        for r in by_parent.get(parent_id, []):
            ordered.append((depth, r))
            _walk(r["id"], depth + 1)

    _walk(None, 0)
    return ordered  # type: ignore[return-value]  -- (depth, row) pairs; see callers


def _heading_level_for_depth(depth: int) -> int:
    # Level 1 is reserved for the document's own top divisions (FINDINGS OF
    # FACT / CONCLUSIONS OF LAW / DECISION OF THE PLANNING BOARD), assembled
    # by build_case_findings_nodes() itself, never by a findings_nodes row.
    # A root section (depth 0) is Code-derived (an Article, a District) ->
    # level 2; its children -> level 3; anything deeper clamps at 4, exactly
    # like style/findings-template.typ's own heading levels are described.
    return min(depth + 2, 4)


_FINDING_SOURCE_LABELS = {"engine": "engine", "model": "model-drafted", "operator": "operator"}


def _source_marker(row: sqlite3.Row) -> list[dict]:
    """A small gray provenance tag naming WHO authored `body` -- 'engine'
    (deterministic), 'model' (LLM-drafted, W6 has none yet), or 'operator'
    (typed by a human). Reuses style/findings-template.typ's existing
    #provenance helper (a generic small-gray-superscript-when-provenance-
    mode-is-on primitive, not citation-specific) rather than adding a second
    template mechanism. Shown only when the PDF is rendered with
    PROVENANCE=1 (render_case_findings()'s `provenance` kwarg) -- the
    Board-facing default omits it, exactly like a citation superscript.
    `finding_source` is a closed 3-value enum (0013_findings_tree.sql's
    CHECK), so no Typst-string escaping is needed for these literals.
    """
    if not row["finding_source"]:
        return []
    label = _FINDING_SOURCE_LABELS.get(row["finding_source"], row["finding_source"])
    return [{"type": "raw", "typst": f'#provenance("{label}")'}]


def _finding_node_to_render_nodes(row: sqlite3.Row, *, ruleset_key: str) -> list[dict]:
    """A `node_type='finding'` row, per CONTRACT.md §10 / 0013_findings_tree.sql:

      quoted_standard_text -- the VERBATIM standard, printed flush left
                               (#standard). Carried on the node itself, not
                               joined from `rules` -- the row is the record.
      body                  -- the Board-facing finding prose beneath it
                               (indented, #finding) -- "facts, not verdicts".
      applicability_verdict -- 'true'/'false'/'unknown'/NULL from the
                               (separately built) applicability gate.
                               UNKNOWN NEVER SUPPRESSES THE NODE: it still
                               renders the standard and asks the Board.
                               'false' means the gate found the standard
                               inapplicable -- still rendered, with whatever
                               reasoning `body` carries (the real decisions'
                               "does not address, and therefore does not
                               apply to, ..." pattern), never silently
                               dropped from the document.

    An absent body/board_question/placeholder still renders, as an
    #unresolved blank, so the section is never silently dropped (the
    decisive W6 test: a case with no facts yet still produces a complete,
    honestly blank walk).
    """
    out: list[dict] = []
    citation_text = (
        _citation_display(row["citation_json"], default_ruleset_key=ruleset_key)
        if row["citation_json"] else None
    )
    if row["quoted_standard_text"]:
        # The criterion letter rides on the standard's first line in a
        # fixed-width box, reproducing the Board's own layout: letter at
        # margin+9pt, standard text and its wrapped lines at margin+27pt.
        out.append(standard(
            row["quoted_standard_text"],
            citation=citation_text,
            label=(row["number_label"] or "").strip() or None,
        ))

    verdict = row["applicability_verdict"]

    if verdict == "unknown":
        # The gate could not determine applicability -- ask the Board rather
        # than guess either way. Never suppressed.
        if row["body"]:
            out.append(finding(row["body"]))
        out.append(boardq(row["board_question"] or "Does this standard apply to this application?"))
        out += _source_marker(row)
        return out

    if row["body"]:
        out.append(finding(row["body"]))
    if row["board_question"]:
        out.append(boardq(row["board_question"]))
    if not row["body"] and not row["board_question"]:
        # Nothing drafted yet for this standard at all (regardless of
        # verdict) -- an honest blank, not an omission. `placeholder`
        # carries the literal 'TBD...' text when the tree-builder supplied
        # one; otherwise a generic one.
        out.append(unresolved(row["placeholder"] or "TBD… (no finding drafted yet for this standard)"))
    out += _source_marker(row)
    return out


def _conclusion_node_to_render_nodes(row: sqlite3.Row) -> list[dict]:
    """A `node_type='conclusion'` row -- the terser "Conclusions of Law"
    restatement the real decisions use (a one-line reference to the
    standard, not its full quoted text -- see e.g. the Uberoi/Shattuck
    samples' lettered a./c./d./... list). `conclusion` itself is always NULL
    here (framing rule); only the restatement text renders.
    """
    label = (row["number_label"] or "").strip()
    text = (row["body"] or row["quoted_standard_text"] or row["heading"] or "").strip()
    if not text:
        return [unresolved("TBD… (no restatement drafted yet)")]
    prefix = f"**{md_escape(label)}.** " if label else ""
    return [para(prefix + md_escape(text))] + _source_marker(row)


def _findings_tree_render_nodes(
    conn: sqlite3.Connection, case_id: str, *, ruleset_key: str,
) -> tuple[list[dict], list[sqlite3.Row]]:
    tree = _load_findings_tree(conn, case_id)
    out: list[dict] = []
    for depth, row in tree:
        node_type = row["node_type"]
        if node_type == "condition_ref":
            continue  # handled separately, as one consolidated Conditions block (see below)
        if node_type in ("section", "required_review"):
            level = _heading_level_for_depth(depth)
            if row["heading"]:
                out.append(heading(row["heading"], level=level))
            if row["body"]:
                out.append(para(md_escape(row["body"])))
        elif node_type == "finding":
            # NO standalone heading for a finding node. MEASURED from the real
            # decisions (Shattuck 2025-12-18 p6, Uberoi 2024-08-15, both in
            # docs/): the criterion letter runs INLINE into the standard's own
            # opening words -- "d.  Sufficient Water: The proposed subdivision
            # has sufficient water available for the reasonably foreseeable
            # needs..." -- on one line hanging at margin+9pt. The Board's
            # documents have no separate "d. Sufficient Water" heading line, so
            # emitting one is our invention, not their house style. The letter
            # is prefixed onto the quoted standard by
            # _finding_node_to_render_nodes() instead.
            out += _finding_node_to_render_nodes(row, ruleset_key=ruleset_key)
        elif node_type == "conclusion":
            out += _conclusion_node_to_render_nodes(row)
        elif node_type == "question":
            out.append(boardq(row["board_question"] or row["body"] or "(question not drafted yet)"))
        elif node_type == "note":
            if row["body"]:
                out.append(para(md_escape(row["body"])))
        else:  # pragma: no cover -- the DDL CHECK already limits node_type to the six above
            out.append(para(md_escape(f"[unrecognized findings_nodes.node_type: {node_type!r}]")))
    return out, [r for _d, r in tree]


# --------------------------------------------------------------------------- #
# Decision block: motions (blank if none recorded yet), conditions, signatures.
# --------------------------------------------------------------------------- #


def _motion_render_nodes(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM motions WHERE case_id = ? ORDER BY sort_order;", (case_id,)
    ).fetchall()
    if not rows:
        # No meeting has produced a real vote yet (W7 territory) -- exactly
        # one genuinely blank slot, matching every pre-meeting DRAFT sample
        # in docs/Findings of Fact and Conclusions of Law/.
        return [motionblock()]

    def _member_name(member_id: str | None) -> str | None:
        if not member_id:
            return None
        row = conn.execute(
            """
            SELECT u.display_name FROM board_members bm
            JOIN users u ON u.id = bm.user_id
            WHERE bm.id = ?;
            """,
            (member_id,),
        ).fetchone()
        return row["display_name"] if row is not None else None

    out: list[dict] = []
    for m in rows:
        out.append(
            motionblock(
                motion=m["text"],
                moved_by=_member_name(m["moved_by"]),
                second=_member_name(m["seconded_by"]),
                yea=None if m["votes_yes"] is None else str(m["votes_yes"]),
                nay=None if m["votes_no"] is None else str(m["votes_no"]),
                abstain=None if m["votes_abstain"] is None else str(m["votes_abstain"]),
                result=m["outcome"],
            )
        )
    return out


def _conditions_render_node(conn: sqlite3.Connection, case_id: str) -> dict:
    rows = conn.execute(
        """
        SELECT * FROM conditions
        WHERE case_id = ? AND superseded_by IS NULL
        ORDER BY number_label, created_at;
        """,
        (case_id,),
    ).fetchall()
    return conditions_node([r["text"] for r in rows])


def _signature_render_node(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT u.display_name AS name, bm.is_chair AS is_chair, bm.seat AS seat
        FROM board_members bm
        JOIN users u ON u.id = bm.user_id
        WHERE bm.term_end IS NULL
        ORDER BY bm.is_chair DESC, u.display_name;
        """
    ).fetchall()
    members = [
        {"name": r["name"], "title": "Chair"} if r["is_chair"] else {"name": r["name"]}
        for r in rows
    ]
    return signaturegrid(members)


# --------------------------------------------------------------------------- #
# The whole document.
# --------------------------------------------------------------------------- #


def build_case_findings_nodes(
    conn: sqlite3.Connection, case_id: str,
) -> tuple[list[dict], list[dict[str, Any]]]:
    """Returns (nodes, unresolved_inventory) for one case's findings draft.

    `unresolved_inventory` is every LIVE findings_nodes row with
    `unresolved = 1` -- the same honest-blanks-list shape
    `render/worksheet.py:build_worksheet_nodes()` already returns for the
    worksheet, so `generated_documents.unresolved_json` (CONTRACT.md §3.6)
    has a consistent meaning across both document kinds.
    """
    case = _get_case_row(conn, case_id)
    ruleset_key = _get_ruleset_key(conn, case["ruleset_id"])

    nodes: list[dict] = [
        heading("Findings of Fact and Conclusions of Law", level=1),
        kv([("Case", case["label"] or "(unlabeled)")]),
        rule(),
        heading("Findings of Fact", level=1),
        heading("Project Information", level=3),
        kv(_project_info_kv(case)),
    ]

    tree_nodes, tree_rows = _findings_tree_render_nodes(conn, case_id, ruleset_key=ruleset_key)
    if tree_nodes:
        nodes += tree_nodes
    else:
        nodes.append(
            boardq(
                "No findings have been drafted for this case yet -- the review engine "
                "(CONTRACT.md W6 items 1-4) has not populated findings_nodes for this case."
            )
        )

    nodes.append(rule())
    nodes.append(heading("Decision of the Planning Board", level=1))
    nodes += _motion_render_nodes(conn, case_id)
    nodes.append(heading("Conditions of Approval", level=3))
    nodes.append(_conditions_render_node(conn, case_id))
    nodes.append(heading("Signatures", level=3))
    nodes.append(_signature_render_node(conn))

    unresolved_inventory: list[dict[str, Any]] = []
    for row in tree_rows:
        if row["unresolved"]:
            unresolved_inventory.append({
                "kind": row["node_type"],
                "id": row["id"],
                "heading": row["heading"],
                "board_question": row["board_question"],
                "citation": _citation_display(row["citation_json"], default_ruleset_key=ruleset_key)
                if row["citation_json"] else None,
            })

    return nodes, unresolved_inventory


def _slug_for_case(case: sqlite3.Row) -> str:
    raw = case["map_lot"] or case["case_number"] or case["id"]
    out = []
    for ch in str(raw).lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "case"


def render_case_findings(
    conn: sqlite3.Connection,
    case_id: str,
    out_dir: Path,
    *,
    draft: bool = True,
    provenance: bool = False,
) -> tuple[Path, list[dict[str, Any]]]:
    """Build + render one findings-draft PDF into `out_dir` (always
    data/exports/, enforced by the caller per CONTRACT.md §1 S5/§8.6).
    Returns (pdf_path, unresolved_inventory).

    Filename: `<YYYYMMDD-HHMMSS>-<case-slug>-findings-draft.pdf`, mirroring
    render/worksheet.py:render_worksheet()'s naming convention exactly.

    `draft` defaults True: CONTRACT.md's framing rule is that every document
    this app produces is a draft until a human Board adopts it at a meeting
    (see render/build-findings.sh's own DRAFT default) -- W6 has no adoption
    workflow yet (that is W7), so there is currently no honest way to call
    this with draft=False for a real case.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    case = _get_case_row(conn, case_id)  # raises CaseNotFound
    nodes, unresolved_inventory = build_case_findings_nodes(conn, case_id)
    md_text = render_nodes(nodes)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slug_for_case(case)
    pdf_name = f"{stamp}-{slug}-findings-draft.pdf"
    pdf_path = out_dir / pdf_name

    md_path = out_dir / f".{stamp}-{slug}-findings-draft.md.tmp"
    md_path.write_text(md_text, encoding="utf-8")

    meeting_date = case["meeting_date"] or ""
    caption = case["label"] or ""
    running_head = "Findings of Fact and Conclusions of Law"

    env = {**__import__("os").environ, "DRAFT": "1" if draft else "0", "PROVENANCE": "1" if provenance else "0"}
    try:
        proc = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(md_path), str(pdf_path), meeting_date, caption, running_head],
            capture_output=True, text=True, timeout=120, env=env,
        )
    finally:
        md_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise FindingsRenderError(
            f"build-findings.sh failed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise FindingsRenderError(f"build-findings.sh reported success but {pdf_path} is missing/empty")

    return pdf_path, unresolved_inventory
