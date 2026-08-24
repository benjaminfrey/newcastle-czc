"""Tests render/case_findings.py -- CONTRACT.md §10, the W6 "draft document"
task: findings_nodes tree -> render node list -> a real PDF via
render/build-findings.sh.

Offline, throwaway temp-dir SQLite (mirrors tests/test_cases.py's `conn`
fixture + `_seed_rulesets`). The end-to-end PDF tests are skipped if pandoc
or typst is not on PATH, exactly like tests/test_render.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import cases, db, security  # noqa: E402
from render import case_findings as cf  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID

HAVE_PANDOC = subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0
HAVE_TYPST = subprocess.run(["which", "typst"], capture_output=True).returncode == 0
HAVE_PDFINFO = subprocess.run(["which", "pdfinfo"], capture_output=True).returncode == 0
requires_toolchain = pytest.mark.skipif(
    not (HAVE_PANDOC and HAVE_TYPST), reason="pandoc and/or typst not on PATH"
)


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_rulesets(c)
    try:
        yield c
    finally:
        c.close()


def _make_case(conn, **overrides) -> dict:
    kwargs = dict(
        application_type="subdivision",
        map_lot="M003, L059",
        situs_address="White Rd",
        applicant_name="Kathleen Shattuck (fictional test fixture)",
        actor_user_id=ACTOR,
    )
    kwargs.update(overrides)
    return cases.create_case(conn, **kwargs)


def _insert_node(conn, *, node_id, case_id, parent_id=None, node_type, sort_order=0, **fields):
    # 0013_findings_tree.sql CHECK: a row carrying `body` or
    # `quoted_standard_text` must carry a non-trivial provenance_json ("a
    # node with prose and an empty provenance object is a bug"). Test rows
    # that supply either get a synthetic provenance object by default,
    # exactly the shape a real engine/model/operator write would carry.
    if "provenance_json" not in fields and (fields.get("body") or fields.get("quoted_standard_text")):
        fields["provenance_json"] = '{"source": "test-fixture"}'
    cols = ["id", "case_id", "parent_id", "sort_order", "node_type", "created_at", "provenance_json"]
    vals = [node_id, case_id, parent_id, sort_order, node_type, "2026-08-20T00:00:00.000Z", "{}"]
    for k, v in fields.items():
        if k == "provenance_json":
            vals[cols.index("provenance_json")] = v
            continue
        cols.append(k)
        vals.append(v)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(f"INSERT INTO findings_nodes ({', '.join(cols)}) VALUES ({placeholders});", vals)


# --------------------------------------------------------------------------- #
# build_case_findings_nodes -- pure node-tree assembly
# --------------------------------------------------------------------------- #


def test_unknown_case_raises_case_not_found(conn):
    with pytest.raises(cf.CaseNotFound):
        cf.build_case_findings_nodes(conn, "not-a-real-case-id")


def test_empty_tree_still_produces_a_complete_walk(conn):
    """THE DECISIVE W6 TEST: a case with NO findings_nodes rows at all still
    renders Project Information, a Decision section with exactly one blank
    motion, one blank condition slot, and a signature grid -- never a short
    or falsely-confident document."""
    case = _make_case(conn)
    nodes, unresolved = cf.build_case_findings_nodes(conn, case["id"])

    kinds = [n["type"] for n in nodes]
    assert "boardq" in kinds  # "no findings drafted yet" flag, not a silent skip
    assert kinds.count("motionblock") == 1
    assert any(n["type"] == "conditions" for n in nodes)
    assert any(n["type"] == "signaturegrid" for n in nodes)
    # No conclusion was ever asserted -- there is nothing in the node list
    # that could render "met"/"not met" (the renderer has no such node type
    # at all, so this also holds structurally, not just for this case).
    assert unresolved == []  # no findings_nodes rows -> nothing to flag as unresolved either


def test_finding_node_renders_standard_then_finding(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n1", case_id=case["id"], node_type="finding",
        heading="D1 - Rural",
        quoted_standard_text="Primary Frontage Line Length (min) Required: 250 ft.",
        body="Proposed frontage: 435 ft.",
    )
    nodes, unresolved = cf.build_case_findings_nodes(conn, case["id"])

    standards = [n for n in nodes if n["type"] == "standard"]
    findings = [n for n in nodes if n["type"] == "finding"]
    assert any("250 ft" in n["text"] for n in standards)
    assert any("435 ft" in n["text"] for n in findings)
    assert unresolved and unresolved[0]["id"] == "n1"  # DDL forces unresolved=1 (no conclusion set)


def test_finding_node_with_no_body_or_question_renders_an_honest_blank(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n2", case_id=case["id"], node_type="finding",
        quoted_standard_text="Setback (min) Required: 20 ft.",
    )
    nodes, _unresolved = cf.build_case_findings_nodes(conn, case["id"])

    unresolved_nodes = [n for n in nodes if n["type"] == "unresolved"]
    assert unresolved_nodes  # never silently dropped
    assert any("TBD" in n["text"] for n in unresolved_nodes)  # a real, non-empty honest blank


def test_applicability_unknown_never_suppresses_the_node(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n_unk", case_id=case["id"], node_type="finding",
        quoted_standard_text="Pollution: the proposed subdivision will not cause undue pollution.",
        applicability_verdict="unknown",
    )
    nodes, unresolved = cf.build_case_findings_nodes(conn, case["id"])

    assert any(n["type"] == "standard" for n in nodes)  # still rendered
    boardqs = [n for n in nodes if n["type"] == "boardq"]
    assert any("apply to this application" in n["text"] for n in boardqs)  # generic fallback question
    assert unresolved and unresolved[0]["id"] == "n_unk"


def test_applicability_false_still_renders_the_standard_and_reasoning(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n_false", case_id=case["id"], node_type="finding",
        quoted_standard_text="Article 3 - Site Standards.",
        applicability_verdict="false",
        body="The standard set forth under Article 3 - Site Standards does not address, "
             "and therefore does not apply to, piers.",
    )
    nodes, _unresolved = cf.build_case_findings_nodes(conn, case["id"])
    assert any(n["type"] == "standard" for n in nodes)
    assert any(n["type"] == "finding" and "does not apply to, piers" in n["text"] for n in nodes)


def test_finding_source_renders_a_provenance_marker_raw_node(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n_src", case_id=case["id"], node_type="finding",
        body="Proposed frontage: 435 ft.", finding_source="engine",
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    raws = [n for n in nodes if n["type"] == "raw"]
    assert any("#provenance(" in n["typst"] and "engine" in n["typst"] for n in raws)


def test_board_question_renders_as_boardq_node(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n3", case_id=case["id"], node_type="question",
        board_question="Does the record establish adequate soils testing?",
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    assert any(
        n["type"] == "boardq" and "soils testing" in n["text"] for n in nodes
    )


def test_conclusion_node_renders_terse_restatement_not_full_standard_text(conn):
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n4", case_id=case["id"], node_type="conclusion",
        number_label="a", body="The standards of this Code.",
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    paras = [n for n in nodes if n["type"] == "para"]
    # md_escape() escapes the trailing "." (markdown-significant) -- check
    # the unescaped substring, and that the bold "a." label prefix is there.
    assert any("The standards of this Code" in n["text"] for n in paras)
    assert any(n["text"].startswith("**a") for n in paras)


def test_condition_ref_node_type_is_skipped_in_the_tree_walk(conn):
    # condition_ref rows are handled once, consolidated, from the
    # `conditions` table -- not scattered through the tree.
    case = _make_case(conn)
    _insert_node(conn, node_id="n5", case_id=case["id"], node_type="condition_ref")
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    # Exactly one conditions() node in the whole document (from the Decision
    # section), not one per condition_ref row.
    assert sum(1 for n in nodes if n["type"] == "conditions") == 1


def test_superseded_finding_node_is_excluded_from_the_current_tree(conn):
    case = _make_case(conn)
    _insert_node(conn, node_id="old1", case_id=case["id"], node_type="note", body="Old text.")
    _insert_node(conn, node_id="new1", case_id=case["id"], node_type="note", body="New text.", revision=2)
    conn.execute("UPDATE findings_nodes SET superseded_by = 'new1' WHERE id = 'old1';")
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    paras = [n["text"] for n in nodes if n["type"] == "para"]
    assert not any("Old text" in t for t in paras)
    assert any("New text" in t for t in paras)


def test_recorded_motion_replaces_the_default_blank_motionblock(conn):
    case = _make_case(conn)
    conn.execute(
        """
        INSERT INTO motions (id, case_id, sort_order, kind, text, votes_yes, votes_no,
                              votes_abstain, outcome, voted_at, recorded_by, created_at)
        VALUES ('m1', ?, 0, 'decision', 'To approve, with conditions.', 5, 0, 0, 'carried',
                '2026-08-20T00:00:00.000Z', ?, '2026-08-20T00:00:00.000Z');
        """,
        (case["id"], ACTOR),
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    motionblocks = [n for n in nodes if n["type"] == "motionblock"]
    assert len(motionblocks) == 1
    assert motionblocks[0]["motion"] == "To approve, with conditions."
    assert motionblocks[0]["yea"] == "5"


def test_signature_grid_lists_sitting_board_members_chair_first(conn):
    case = _make_case(conn)
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_a', 'A. Member', 'board_member', '2026-08-20T00:00:00.000Z'), "
        "('u_b', 'B. Chairperson', 'chair', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, is_chair, term_start, created_at) VALUES "
        "('bm_a', 'u_a', 0, '2026-01-01', '2026-08-20T00:00:00.000Z'), "
        "('bm_b', 'u_b', 1, '2026-01-01', '2026-08-20T00:00:00.000Z');"
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    grid = next(n for n in nodes if n["type"] == "signaturegrid")
    assert grid["members"][0] == {"name": "B. Chairperson", "title": "Chair"}
    assert grid["members"][1] == {"name": "A. Member"}


def test_signature_grid_prefers_recorded_attendance_over_every_sitting_member(conn):
    # Mirrors the real Blood and Sons adopted final: 7 sitting seats, but
    # only the 5 who actually attended sign -- render/case_findings.py must
    # follow the roll call, not just list whoever currently holds a seat.
    case = _make_case(conn)
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_a', 'A. Member', 'board_member', '2026-08-20T00:00:00.000Z'), "
        "('u_b', 'B. Chairperson', 'chair', '2026-08-20T00:00:00.000Z'), "
        "('u_c', 'C. Absent', 'board_member', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, is_chair, term_start, created_at) VALUES "
        "('bm_a', 'u_a', 0, '2026-01-01', '2026-08-20T00:00:00.000Z'), "
        "('bm_b', 'u_b', 1, '2026-01-01', '2026-08-20T00:00:00.000Z'), "
        "('bm_c', 'u_c', 0, '2026-01-01', '2026-08-20T00:00:00.000Z');"
    )
    # Only A and B attended this case's meeting; C never got an attendance row.
    conn.execute(
        "INSERT INTO attendance (id, case_id, board_member_id, present, recorded_at, "
        "created_at) VALUES "
        "('att_a', ?, 'bm_a', 1, '2026-08-20T00:00:00.000Z', '2026-08-20T00:00:00.000Z'), "
        "('att_b', ?, 'bm_b', 1, '2026-08-20T00:00:00.000Z', '2026-08-20T00:00:00.000Z');",
        (case["id"], case["id"]),
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    grid = next(n for n in nodes if n["type"] == "signaturegrid")
    names = [m["name"] for m in grid["members"]]
    assert names == ["B. Chairperson", "A. Member"]
    assert "C. Absent" not in names


# --------------------------------------------------------------------------- #
# Conflict of Interest Disclosures -- app/meeting.py's write side;
# render/case_findings.py's `_conflict_disclosures_render_node()` here is
# the read side. The zero-rows case is the decisive test (W7 task brief):
# it must render as the real DRAFT samples do -- an honest TBD blank --
# and NEVER as "no conflicts declared".
# --------------------------------------------------------------------------- #


def test_conflict_disclosures_zero_rows_renders_tbd_never_none_declared(conn):
    case = _make_case(conn)
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    idx = next(i for i, n in enumerate(nodes) if n["type"] == "heading" and n["text"] == "Conflict of Interest Disclosures")
    body = nodes[idx + 1]
    assert body["type"] == "unresolved"
    assert body["text"] == "TBD…"
    # It must never, under any circumstance, read as an actual finding of
    # "no conflicts" when no roll call has happened.
    all_text = " ".join(n.get("text", "") for n in nodes)
    assert "No Planning Board members identified" not in all_text
    assert "no conflicts declared" not in all_text.lower()


def test_conflict_disclosures_none_disclosed_renders_the_real_wording(conn):
    case = _make_case(conn)
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_a', 'A. Member', 'board_member', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, term_start, created_at) VALUES "
        "('bm_a', 'u_a', '2026-01-01', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO conflict_disclosures (id, case_id, board_member_id, disclosed, recused, "
        "created_at) VALUES ('cd_a', ?, 'bm_a', 0, 0, '2026-08-20T00:00:00.000Z');",
        (case["id"],),
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    idx = next(i for i, n in enumerate(nodes) if n["type"] == "heading" and n["text"] == "Conflict of Interest Disclosures")
    body = nodes[idx + 1]
    assert body["type"] == "para"
    assert body["text"] == (
        "No Planning Board members identified any potential conflicts of "
        "interest in taking up the submitted application for review."
    )


def test_conflict_disclosures_disclosed_narrates_the_recusal(conn):
    case = _make_case(conn)
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_a', 'A. Member', 'board_member', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, term_start, created_at) VALUES "
        "('bm_a', 'u_a', '2026-01-01', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO conflict_disclosures (id, case_id, board_member_id, disclosed, recused, "
        "nature, created_at) VALUES "
        "('cd_a', ?, 'bm_a', 1, 1, 'abutting property owner', '2026-08-20T00:00:00.000Z');",
        (case["id"],),
    )
    nodes, _ = cf.build_case_findings_nodes(conn, case["id"])
    idx = next(i for i, n in enumerate(nodes) if n["type"] == "heading" and n["text"] == "Conflict of Interest Disclosures")
    body = nodes[idx + 1]
    assert body["type"] == "para"
    # md_escape() escapes the period in "A. Member" (a DB-sourced string,
    # correctly escaped before it reaches para() per this module's own
    # docstring) -- assert on the un-escaped substrings either side of it.
    assert "A" in body["text"] and "Member" in body["text"]
    assert "abutting property owner" in body["text"]
    assert "recused" in body["text"]


# --------------------------------------------------------------------------- #
# render_case_findings -- end to end, a real PDF
# --------------------------------------------------------------------------- #


@requires_toolchain
def test_render_case_findings_produces_a_real_pdf(conn):
    # render/build-findings.sh hard-refuses to write outside APP/data/exports/
    # (CONTRACT.md §6.3/§8.6) -- a tmp_path dir is rejected by design, exactly
    # like tests/test_render.py's own end-to-end test. data/ is scratch and
    # gitignored; the file is removed again below, leaving no litter.
    case = _make_case(conn)
    _insert_node(
        conn, node_id="n1", case_id=case["id"], node_type="section",
        heading="Article 2 - District Standards", sort_order=0,
    )
    _insert_node(
        conn, node_id="n2", case_id=case["id"], parent_id="n1", node_type="finding",
        heading="D1 - Rural",
        quoted_standard_text="Primary Frontage Line Length (min) Required: 250 ft.",
        body="Proposed frontage: 435 ft.", finding_source="engine", sort_order=1,
    )

    out_dir = APP_ROOT / "data" / "exports"
    pdf_path, unresolved = cf.render_case_findings(conn, case["id"], out_dir)
    try:
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        assert any(u["id"] == "n2" for u in unresolved)

        if HAVE_PDFINFO:
            info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True)
            match = re.search(r"^Pages:\s+(\d+)", info.stdout, re.MULTILINE)
            assert match is not None and int(match.group(1)) >= 1
    finally:
        pdf_path.unlink(missing_ok=True)


def test_render_case_findings_unknown_case_raises_before_any_subprocess(conn, tmp_path):
    out_dir = tmp_path / "exports"
    with pytest.raises(cf.CaseNotFound):
        cf.render_case_findings(conn, "not-a-real-case-id", out_dir)
    # The directory may exist (render_case_findings mkdir's it up front, like
    # render/worksheet.py does), but no PDF or markdown was ever written --
    # the CaseNotFound check runs before any subprocess call.
    assert list(out_dir.glob("*")) == [] if out_dir.exists() else True
