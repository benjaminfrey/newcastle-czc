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
`findings_nodes` tree, and the `motions`/`conditions`/`board_members`/
`conflict_disclosures`/`attendance` tables (the last two, W7's "meeting
model" -- app/meeting.py is their write side; this module only reads them,
same split as everything else here) -- and turns them into the
`render.findings_to_md` node list that
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

ALSO IN THIS FILE (W7, added below render_case_findings()): the ADOPTED
FINAL. `render_adopted_final()` reuses the SAME build_case_findings_nodes()
+ render.findings_to_md.render_nodes() + build-findings.sh pipeline as
render_case_findings() above -- draft=False, provenance=False -- gated by
`verify_adopted()`, which refuses (NotAdoptedError) unless a real carried
adoption motion (verbatim wording, see ADOPTION_MOTION_TEXT) and a real
recorded Board decision already exist, AND every live findings_nodes row
for the case is itself resolved (unresolved = 0 -- see
`_check_no_unresolved_findings()`, added in the 2026-08-23 repair pass: a
carried generic adoption motion does not, by itself, prove every individual
standard was actually voted on). See that section's own block
comment for the full rationale, the D-0026/D-0028 reproduction notes, and
`downstream_clocks()` (§8.f.1 Clerk filing -> §23.d.1 appeal window, via
engine/deadlines.py -- no clock arithmetic reimplemented here).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import citation as citation_mod  # noqa: E402
from engine import deadlines as deadlines_mod  # noqa: E402
from engine import findings  # noqa: E402
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
# Conflict of Interest Disclosures -- W7's "the meeting model" (app/meeting.py).
# Printed in FINDINGS OF FACT, right after Project Information, exactly where
# every real sample in docs/Findings of Fact and Conclusions of Law/ puts it.
# --------------------------------------------------------------------------- #


def _conflict_disclosures_render_node(conn: sqlite3.Connection, case_id: str) -> dict:
    """Three cases, matching app/meeting.py:conflict_disclosures_summary():

      - ZERO rows -- no roll call recorded yet. An honest "TBD..." blank,
        NEVER "no conflicts declared" (absence of a record is not a finding
        of none) -- matches every pre-meeting DRAFT sample verbatim
        (Buehner, Verney, Blood and Sons, Z38 all print "TBD...").
      - rows exist, none disclosed -- the real adopted-final wording,
        verbatim from Shattuck/Uberoi.
      - rows exist, one or more disclosed -- narrated per disclosing member;
        DB-sourced text (name, nature) is md_escape()'d before it reaches
        para(), same rule this module's docstring states for every other
        DB-sourced string.
    """
    rows = conn.execute(
        """
        SELECT cd.disclosed, cd.recused, cd.nature, u.display_name AS member_name
        FROM conflict_disclosures cd
        JOIN board_members bm ON bm.id = cd.board_member_id
        JOIN users u ON u.id = bm.user_id
        WHERE cd.case_id = ?
        ORDER BY u.display_name;
        """,
        (case_id,),
    ).fetchall()
    if not rows:
        return unresolved("TBD…")

    disclosed_rows = [r for r in rows if r["disclosed"]]
    if not disclosed_rows:
        return para(
            "No Planning Board members identified any potential conflicts of "
            "interest in taking up the submitted application for review."
        )

    sentences = []
    for r in disclosed_rows:
        name = md_escape(r["member_name"])
        nature = f" ({md_escape(r['nature'])})" if r["nature"] else ""
        verb = "recused from consideration of this application" if r["recused"] else "did not recuse"
        sentences.append(f"{name} disclosed a conflict of interest{nature} and {verb}.")
    return para(" ".join(sentences))


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


def _signature_render_node(conn: sqlite3.Connection, case_id: str) -> dict:
    """Who signs. Prefers this case's own recorded `attendance` roll call
    (present = 1) -- the real decisions sign only the members who were
    actually there: Blood and Sons's adopted final has FIVE signature
    lines against SEVEN sitting seats, matching its "five (5) in favor"
    vote. Before a meeting has been held (no attendance rows yet for this
    case -- the normal state before W7's meeting workflow), falls back to
    every currently-sitting member, same as before this fell back to
    attendance: an honest "whoever is on the Board could sign" blank
    slate, matching every pre-meeting DRAFT sample.
    """
    rows = conn.execute(
        """
        SELECT u.display_name AS name, bm.is_chair AS is_chair
        FROM attendance a
        JOIN board_members bm ON bm.id = a.board_member_id
        JOIN users u ON u.id = bm.user_id
        WHERE a.case_id = ? AND a.present = 1
        ORDER BY bm.is_chair DESC, u.display_name;
        """,
        (case_id,),
    ).fetchall()
    if not rows:
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
        heading("Conflict of Interest Disclosures", level=3),
        _conflict_disclosures_render_node(conn, case_id),
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
    nodes.append(_signature_render_node(conn, case_id))

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


# =============================================================================
# W7 task: "the adopted final + downstream clocks".
#
# NOT a second renderer -- render_adopted_final() below reuses exactly the
# same two building blocks render_case_findings() above already uses
# (build_case_findings_nodes() + render.findings_to_md.render_nodes()) and
# the same render/build-findings.sh + style/findings-template.typ pipeline,
# called with draft=False (no DRAFT watermark) and provenance=False (no
# gray citation-source tags) -- exactly the shape every real ADOPTED sample
# in docs/Findings of Fact and Conclusions of Law/ has, as opposed to the
# DRAFT samples render_case_findings() reproduces above.
#
# THE ONE THING THIS SECTION ADDS: it refuses to run at all unless a REAL
# recorded adoption vote already exists (verify_adopted() below) -- this is
# the ONE place in the app allowed to call a document "final", and even
# here it never supplies a fact itself. Every outcome/vote it reads was
# written by app/meeting.py's record_vote()/record_outcome(), both of which
# REQUIRE a named human (recorded_by) and a timestamp before either can set
# an outcome at all -- 0001_init.sql's own CHECK constraints are the
# backstop; this module's job is only to check those facts are PRESENT, not
# to supply them.
#
# VERBATIM ADOPTION WORDING (the W7 task brief: "lift it from the document,
# do not compose it"). ADOPTION_MOTION_TEXT below is copied character-for-
# character from the one ADOPTED (not draft) sample in
# docs/Findings of Fact and Conclusions of Law/ --
# "M003, L059 (White Road, Shattuck), Subdivision FoF & CoL 2025.12.18.pdf",
# page 14 of 16, the "Findings Of Fact" motion block (`pdftotext -layout`,
# line 759 of the extracted text; independently re-verified while writing
# this section, 2026-08-23):
#
#     Motion:  To accept and adopt the draft findings of fact and
#              conclusions of law, as amended.
#
# TWO THINGS THIS SECTION REPRODUCES ON PURPOSE, NOT BY OVERSIGHT (see
# DECISIONS-NEEDED.md):
#   - D-0028: the certification block (style/findings-template.typ's
#     #signaturegrid caption) reads "Findings of Fact and CONDITIONS of Law"
#     -- present in all nine samples, including this same adopted one. This
#     section does not touch it, and does not "fix" it. Correcting it is
#     the Board's call.
#   - D-0026: no appeal-rights paragraph is added anywhere in this
#     pipeline. None of the nine samples has one. Writing one would put
#     text of legal effect in front of the Board that no lawyer approved --
#     exactly the failure CONTRACT.md's framing rule exists to prevent. The
#     §23 appeal window's DATES are computed by downstream_clocks() below
#     and are available to whoever eventually drafts that paragraph; this
#     section supplies no wording.
# =============================================================================

# See the block comment above for this string's exact provenance -- copied
# verbatim from the one ADOPTED sample in docs/, never composed here.
ADOPTION_MOTION_TEXT = "To accept and adopt the draft findings of fact and conclusions of law, as amended."


class NotAdoptedError(RuntimeError):
    """Raised when render_adopted_final() is asked to produce an adopted
    final for a case that has no recorded adoption vote (and/or no recorded
    disposition vote) yet. There is no override -- this module will not
    treat a draft tree as adopted no matter who asks."""


def _find_adoption_motion(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    """The one `motions` row (kind='findings') whose text is the verbatim
    adoption wording AND whose outcome is 'carried'. A strict match,
    deliberately: this module has no business guessing that some OTHER
    'findings'-kind motion was "close enough" to count as adoption.
    """
    rows = conn.execute(
        "SELECT * FROM motions WHERE case_id = ? AND kind = 'findings' ORDER BY sort_order;",
        (case_id,),
    ).fetchall()
    for row in rows:
        if (row["text"] or "").strip() == ADOPTION_MOTION_TEXT and row["outcome"] == "carried":
            if row["recorded_by"] is None or row["voted_at"] is None:
                # Can't actually happen -- 0001_init.sql's own CHECK forbids
                # an outcome without both -- but this module treats that
                # CHECK as a backstop, not as license to skip checking here.
                continue
            return row
    raise NotAdoptedError(
        f"case {case_id!r}: no carried adoption motion found (kind='findings', "
        f"text == {ADOPTION_MOTION_TEXT!r}). Record the vote (app.meeting.record_vote) "
        "before producing an adopted final."
    )


def _find_decision(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    """The most recent `decisions` row for this case with a non-NULL
    `outcome` (app.meeting.record_outcome's write path). Raises
    NotAdoptedError if none exists yet."""
    row = conn.execute(
        """
        SELECT * FROM decisions
        WHERE case_id = ? AND outcome IS NOT NULL
        ORDER BY decided_at DESC, created_at DESC
        LIMIT 1;
        """,
        (case_id,),
    ).fetchone()
    if row is None:
        raise NotAdoptedError(
            f"case {case_id!r}: no recorded Board decision (a `decisions` row with a "
            "non-NULL outcome) found. Record the disposition vote (app.meeting.record_outcome) "
            "before producing an adopted final."
        )
    if row["recorded_by"] is None or row["decided_at"] is None:
        raise NotAdoptedError(
            f"case {case_id!r}: decision row {row['id']!r} has an outcome but is missing "
            "recorded_by/decided_at -- not a genuinely recorded human act."
        )
    return row


def _check_no_unresolved_findings(conn: sqlite3.Connection, case_id: str) -> None:
    """REPAIR (2026-08-23, F-1): a carried adoption motion + a recorded
    decision are NECESSARY but not SUFFICIENT. CONTRACT.md's framing rule --
    restated at the top of this module -- is "every conclusion traces to a
    motion, a vote, and a named human." That is only actually true once
    every LIVE (superseded_by IS NULL) findings_nodes row for this case is
    itself resolved (unresolved = 0).

    Without this check, the generic "accept and adopt ... as amended"
    motion could carry while individual finding/conclusion nodes still sit
    un-concluded -- never drafted, or behind a motion that was tabled or
    that FAILED (engine.meeting.apply_motion() correctly refuses to write a
    conclusion for anything but a carried motion, so a failed vote leaves
    the node's stale drafted prose in place, unresolved, forever) -- and
    render_adopted_final() would still print a document with no DRAFT
    watermark: a "final" that silently contains standards nobody's vote
    ever actually closed. `unresolved` defaults to 1 for every
    finding/conclusion/question/condition_ref node and is flipped to 0 only
    by engine.findings._write_conclusion() (engine.meeting.apply_motion()'s
    one write); section/note/required_review headers are created with
    unresolved=0 up front (engine/subdivision_review.py) and so never
    appear here. `build_case_findings_nodes()`'s own `unresolved_inventory`
    -- already computed on every render, already persisted verbatim into
    generated_documents.unresolved_json -- carried this exact signal all
    along; this function is the first thing to actually gate on it rather
    than just record it for posterity.
    """
    rows = conn.execute(
        """
        SELECT id, node_type, heading, number_label
        FROM findings_nodes
        WHERE case_id = ? AND superseded_by IS NULL AND unresolved = 1
        ORDER BY sort_order;
        """,
        (case_id,),
    ).fetchall()
    if not rows:
        return
    labels = [
        f"{(r['number_label'] or '').strip() or r['node_type']} ({r['id']})"
        for r in rows[:5]
    ]
    more = f", and {len(rows) - 5} more" if len(rows) > 5 else ""
    raise NotAdoptedError(
        f"case {case_id!r}: {len(rows)} findings_nodes row(s) are still unresolved -- "
        f"no recorded Conclusion of Law -- {', '.join(labels)}{more}. Every live finding/"
        "conclusion node must be closed by a carried, APPLIED motion "
        "(app.meeting.draft_node_motion -> app.meeting.record_vote -> "
        "engine.meeting.apply_motion) before an adopted final can be produced."
    )


def verify_adopted(conn: sqlite3.Connection, case_id: str) -> tuple[sqlite3.Row, sqlite3.Row]:
    """Returns (adoption_motion_row, decision_row), or raises NotAdoptedError.
    The one gate this whole section exists to enforce."""
    motion = _find_adoption_motion(conn, case_id)
    decision = _find_decision(conn, case_id)
    _check_no_unresolved_findings(conn, case_id)
    # Every conclusion about to be printed as adopted must trace to a carried
    # motion. The DB CHECK proves a conclusion was ATTRIBUTED to a human; only
    # this proves a VOTE stands behind it (engine/findings.OrphanConclusionError
    # documents why the two are different). Checked here, at the adoption gate,
    # because this is the last point before text becomes the Board's final word.
    findings.assert_no_orphan_conclusions(conn, case_id)
    return motion, decision


# --------------------------------------------------------------------------- #
# The node-tree snapshot. Captured as DATA (not left implicit in "whatever
# findings_nodes/motions/conditions look like right now"), so the adopted
# text stays recoverable byte-for-byte even after the live tree moves on --
# CONTRACT.md §3.6's append-only/amendment model means it always can (a
# later amendment on some OTHER case's node with the same rule_id, a future
# board_members roster change, ...).
# --------------------------------------------------------------------------- #


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _motion_snapshot(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM motions WHERE case_id = ? ORDER BY sort_order;", (case_id,)).fetchall()

    def _member_name(member_id: Optional[str]) -> Optional[str]:
        if not member_id:
            return None
        r = conn.execute(
            "SELECT u.display_name FROM board_members bm JOIN users u ON u.id = bm.user_id WHERE bm.id = ?;",
            (member_id,),
        ).fetchone()
        return r["display_name"] if r is not None else None

    out = []
    for m in rows:
        d = _row_to_dict(m)
        d["moved_by_name"] = _member_name(m["moved_by"])
        d["seconded_by_name"] = _member_name(m["seconded_by"])
        out.append(d)
    return out


def _conditions_snapshot(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM conditions
        WHERE case_id = ? AND superseded_by IS NULL
        ORDER BY number_label, created_at;
        """,
        (case_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _findings_tree_snapshot(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """The CURRENT (superseded_by IS NULL) tree only, deliberately -- an
    adopted final is the document the Board actually voted on at THIS
    meeting; earlier superseded revisions stay recoverable through
    findings_nodes' own append-only history, but they are not part of what
    was adopted."""
    rows = conn.execute(
        "SELECT * FROM findings_nodes WHERE case_id = ? AND superseded_by IS NULL ORDER BY sort_order;",
        (case_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _signature_snapshot(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    return _signature_render_node(conn, case_id)["members"]


def build_node_tree_snapshot(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    """Everything render_case_findings()/render_adopted_final() reads to
    build the document, captured as plain data: the case, the live
    findings_nodes tree, motions (including the adoption + decision motions
    this render required), conditions, the decision row, and the signing
    board membership at the moment of adoption. This is the "NODE-TREE
    SNAPSHOT" the W7 brief asks for -- independent of anything that happens
    to findings_nodes, motions, or board_members afterward.
    """
    case = _get_case_row(conn, case_id)
    adoption_motion, decision = verify_adopted(conn, case_id)
    return {
        "schema": "adopted_final_snapshot.v1",
        "case": _row_to_dict(case),
        "findings_nodes": _findings_tree_snapshot(conn, case_id),
        "motions": _motion_snapshot(conn, case_id),
        "conditions": _conditions_snapshot(conn, case_id),
        "decision": _row_to_dict(decision),
        "adoption_motion_id": adoption_motion["id"],
        "signatures": _signature_snapshot(conn, case_id),
    }


def canonical_bytes(obj: Any) -> bytes:
    """The SAME canonicalization CONTRACT.md §3.3 mandates for events-table
    hashing (sort_keys, no extraneous whitespace, ensure_ascii=False) --
    reused here rather than invented fresh, so "canonical JSON" means one
    thing across this codebase."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def snapshot_sha256(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()


# --------------------------------------------------------------------------- #
# render_adopted_final -- reuses build_case_findings_nodes() + render_nodes()
# (the exact two calls render_case_findings() above makes) and the same
# build-findings.sh pipeline. Persists md permanently (unlike
# render_case_findings()'s throwaway .md.tmp) because the W7 brief requires
# storing md alongside pdf + sha256 + snapshot.
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class AdoptedFinalResult:
    pdf_path: Path
    md_path: Path
    snapshot_path: Path
    content_sha256: str  # sha256 of the markdown TEXT -- the reproducible "same tree, same
    #                       votes -> same content" identity (0018_adopted_final.sql).
    pdf_sha256: str       # sha256 of the actual PDF file bytes -- NOT expected to reproduce
    #                       run to run: Typst stamps wall-clock CreationDate/ModDate into
    #                       every PDF it writes (verified empirically, 2026-08-23, before
    #                       this module was written -- see 0018_adopted_final.sql's header).
    #                       Kept for file-integrity purposes only.
    pdf_byte_size: int
    snapshot: dict[str, Any]
    unresolved_inventory: list[dict[str, Any]]
    adoption_motion_id: str
    decision_id: str


def render_adopted_final(conn: sqlite3.Connection, case_id: str, out_dir: Path) -> AdoptedFinalResult:
    """Produce the adopted-final PDF + md + node-tree snapshot for `case_id`.

    Raises CaseNotFound / NotAdoptedError / FindingsRenderError; writes
    nothing to the database itself -- mirrors render_case_findings()'s own
    split: this is a pure render, the caller (the HTTP route) is
    responsible for the generated_documents + events transaction, exactly
    like POST /api/cases/{id}/findings/render already does for the draft.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    case = _get_case_row(conn, case_id)  # raises CaseNotFound
    adoption_motion, decision = verify_adopted(conn, case_id)  # raises NotAdoptedError

    nodes, unresolved_inventory = build_case_findings_nodes(conn, case_id)
    md_text = render_nodes(nodes)

    snapshot = build_node_tree_snapshot(conn, case_id)
    content_sha = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
    snapshot["content_sha256"] = content_sha  # cross-check: the exact text this snapshot's
    #                                            tree/motions/conditions/decision produced

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slug_for_case(case)
    base = f"{stamp}-{slug}-findings-final"

    md_path = out_dir / f"{base}.md"
    pdf_path = out_dir / f"{base}.pdf"
    snapshot_path = out_dir / f"{base}.snapshot.json"

    md_path.write_text(md_text, encoding="utf-8")
    # snapshot_generated_at is record-keeping only -- deliberately NOT folded
    # into content_sha256/snapshot_sha256, so two adopted-final renders of
    # the identical tree/votes still hash identically despite being produced
    # at different wall-clock moments (the W7 brief's own reproducibility
    # requirement).
    snapshot_on_disk = dict(snapshot, snapshot_generated_at=datetime.now(timezone.utc).isoformat())
    snapshot_path.write_text(
        json.dumps(snapshot_on_disk, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    meeting_date = case["meeting_date"] or ""
    caption = case["label"] or ""
    running_head = "Findings of Fact and Conclusions of Law"

    import os

    env = {**os.environ, "DRAFT": "0", "PROVENANCE": "0"}
    try:
        proc = subprocess.run(
            ["bash", str(BUILD_SCRIPT), str(md_path), str(pdf_path), meeting_date, caption, running_head],
            capture_output=True, text=True, timeout=120, env=env,
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced as FindingsRenderError below
        raise FindingsRenderError(f"build-findings.sh could not be run: {exc}") from exc

    if proc.returncode != 0:
        raise FindingsRenderError(
            f"build-findings.sh failed (exit {proc.returncode}):\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise FindingsRenderError(f"build-findings.sh reported success but {pdf_path} is missing/empty")

    pdf_bytes = pdf_path.read_bytes()

    return AdoptedFinalResult(
        pdf_path=pdf_path,
        md_path=md_path,
        snapshot_path=snapshot_path,
        content_sha256=content_sha,
        pdf_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        pdf_byte_size=len(pdf_bytes),
        snapshot=snapshot,
        unresolved_inventory=unresolved_inventory,
        adoption_motion_id=adoption_motion["id"],
        decision_id=decision["id"],
    )


# --------------------------------------------------------------------------- #
# downstream_clocks -- does NOT reimplement any clock arithmetic. Reads
# engine/deadlines.py's own CaseFacts/compute_deadlines exactly as
# app/main.py's _compute_deadlines_safe() already does for the case-detail
# page, from whatever case_milestones rows are actually recorded. The
# caller (the HTTP route) is responsible for feeding the 'decision_issued'
# milestone through app.cases.record_dates() BEFORE calling this -- that is
# the one thing that has to happen for the decision -> Clerk-filing ->
# appeal-window chain to compute at all.
# --------------------------------------------------------------------------- #


DOWNSTREAM_CLOCK_KEYS = ("decision_filed_with_clerk", "administrative_appeal")


def downstream_clocks(
    conn: sqlite3.Connection, case_id: str, *, as_of: Optional[date] = None,
) -> list[deadlines_mod.Deadline]:
    """The two clocks the W7 brief names by citation -- §8.f.1 (decision
    filed with the Town Clerk, 5 business days) and §23.d.1 (the
    administrative appeal window it starts) -- computed from whatever
    case_milestones rows this case actually has right now.

    `administrative_appeal` reports PENDING_START (no due_date yet) unless
    a 'decision_filed' milestone has ALSO been recorded -- the Code's own
    text: the Clerk's date stamp is what starts the appeal window, not the
    decision itself. That is correct, honest behaviour, not a limitation.
    """
    case_row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if case_row is None:
        raise CaseNotFound(case_id)
    ruleset_row = conn.execute(
        "SELECT ruleset_key FROM rulesets WHERE id = ?;", (case_row["ruleset_id"],)
    ).fetchone()
    merged = dict(case_row)
    merged["ruleset_key"] = ruleset_row["ruleset_key"] if ruleset_row is not None else "adopted"

    milestone_rows = conn.execute(
        "SELECT * FROM case_milestones WHERE case_id = ? ORDER BY created_at;", (case_id,)
    ).fetchall()
    facts = deadlines_mod.case_facts_from_row(merged, milestone_rows)
    all_deadlines = deadlines_mod.compute_deadlines(facts, as_of=as_of, include_meeting_clocks=False)
    return [d for d in all_deadlines if d.clock_key in DOWNSTREAM_CLOCK_KEYS]
