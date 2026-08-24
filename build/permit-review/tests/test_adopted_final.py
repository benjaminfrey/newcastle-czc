"""Tests render/case_findings.py's W7 addition -- render_adopted_final(),
verify_adopted(), and downstream_clocks().

Offline, throwaway temp-dir SQLite, mirroring tests/test_meeting.py's own
`conn`/`_make_case`/`_seed_board` fixtures (reused directly, not
duplicated). The end-to-end render tests are skipped if pandoc or typst is
not on PATH, exactly like tests/test_case_findings.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import cases, db, meeting, security  # noqa: E402
from engine import meeting as meeting_engine  # noqa: E402
from render import case_findings as cf  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402
from tests.test_meeting import _make_case, _seed_board  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID

HAVE_PANDOC = subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0
HAVE_TYPST = subprocess.run(["which", "typst"], capture_output=True).returncode == 0
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


def _insert_finding_node(conn, *, case_id, node_id="n1"):
    conn.execute(
        """
        INSERT INTO findings_nodes
            (id, case_id, parent_id, sort_order, node_type, heading,
             quoted_standard_text, body, provenance_json, created_at)
        VALUES (?, ?, NULL, 0, 'finding', 'd. Sufficient Water',
                'Sufficient Water (min): the subdivision must have sufficient water available.',
                'The proposed subdivision has sufficient water available (fictional test fixture).',
                '{"source": "test-fixture"}', '2026-08-20T00:00:00.000Z');
        """,
        (node_id, case_id),
    )


def _resolve_finding_node(conn, *, case_id, node_id, bm_chair, bm_member) -> dict:
    """Genuinely closes one findings_nodes row the same way a real Board
    meeting does: draft the per-node motion (app.meeting.draft_node_motion,
    prefilled from the node), record a carried vote, then apply it
    (engine.meeting.apply_motion -- the one and only writer of
    findings_nodes.conclusion). Returns the node after apply_motion().

    Added in the 2026-08-23 repair pass alongside
    render.case_findings._check_no_unresolved_findings(): before that fix,
    _adopt_case() alone (a carried GENERIC adoption motion + a recorded
    decision) was enough to make verify_adopted()/render_adopted_final()
    treat a case as adopted even though this specific standard had never
    been voted on -- see test_verify_adopted_refuses_when_a_live_finding_
    is_still_unresolved below, which reproduces that exact gap and proves
    it is now closed. The two render tests below now call this FIRST so
    they exercise the genuinely-complete path the fix requires."""
    motion = meeting.draft_node_motion(conn, case_id=case_id, node_id=node_id, actor_user_id=ACTOR)
    voted = meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, voted_at="2025-12-18T18:20:00.000Z", actor_user_id=ACTOR,
    )
    meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)
    return conn.execute("SELECT * FROM findings_nodes WHERE id = ?;", (node_id,)).fetchone()


def _adopt_case(conn, *, case_id, ruleset_id, bm_chair, bm_member) -> tuple[dict, dict]:
    """Drives the full W7 motion sequence (app.meeting) to a genuinely
    adopted state: a carried adoption motion with the VERBATIM wording, and
    a recorded decision. Returns (adoption_motion_row, decision_row)."""
    m = meeting.create_motion(
        conn, case_id=case_id, kind="findings", text=cf.ADOPTION_MOTION_TEXT,
        sort_order=90, actor_user_id=ACTOR,
    )
    m = meeting.record_vote(
        conn, motion_id=m["id"], moved_by=bm_member, seconded_by=bm_chair,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, voted_at="2025-12-18T18:30:00.000Z", actor_user_id=ACTOR,
    )
    decision_motion = meeting.create_motion(
        conn, case_id=case_id, kind="decision",
        text="To approve, with conditions, the subdivision application as discussed and amended.",
        sort_order=100, actor_user_id=ACTOR,
    )
    meeting.record_vote(
        conn, motion_id=decision_motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, voted_at="2025-12-18T18:35:00.000Z", actor_user_id=ACTOR,
    )
    decision = meeting.record_outcome(
        conn, case_id=case_id, ruleset_id=ruleset_id, outcome="approved_with_conditions",
        recorded_by=ACTOR, motion_id=decision_motion["id"], decided_at="2025-12-18",
        meeting_date="2025-12-18", summary="Approved with conditions (fictional test fixture).",
        actor_user_id=ACTOR,
    )
    return m, decision


# --------------------------------------------------------------------------- #
# verify_adopted() / NotAdoptedError -- THE gate.
# --------------------------------------------------------------------------- #


def test_no_motions_at_all_raises_not_adopted(conn):
    case = _make_case(conn)
    with pytest.raises(cf.NotAdoptedError):
        cf.verify_adopted(conn, case["id"])


def test_a_findings_motion_that_failed_does_not_count_as_adoption(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    m = meeting.create_motion(
        conn, case_id=case["id"], kind="findings", text=cf.ADOPTION_MOTION_TEXT, actor_user_id=ACTOR,
    )
    meeting.record_vote(
        conn, motion_id=m["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=1, votes_no=1, votes_abstain=0, outcome="failed",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    with pytest.raises(cf.NotAdoptedError):
        cf.verify_adopted(conn, case["id"])


def test_a_carried_findings_motion_with_the_wrong_wording_does_not_count(conn):
    """This module refuses to guess that a differently-worded 'findings'
    motion was "close enough" -- the adoption wording must be VERBATIM."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    m = meeting.create_motion(
        conn, case_id=case["id"], kind="findings",
        text="To adopt the findings of fact.",  # NOT the verbatim wording
        actor_user_id=ACTOR,
    )
    meeting.record_vote(
        conn, motion_id=m["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    with pytest.raises(cf.NotAdoptedError):
        cf.verify_adopted(conn, case["id"])


def test_carried_adoption_motion_but_no_decision_still_raises(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    m = meeting.create_motion(
        conn, case_id=case["id"], kind="findings", text=cf.ADOPTION_MOTION_TEXT, actor_user_id=ACTOR,
    )
    meeting.record_vote(
        conn, motion_id=m["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    with pytest.raises(cf.NotAdoptedError):
        cf.verify_adopted(conn, case["id"])


def test_fully_adopted_case_passes_verify_adopted(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    motion, decision = _adopt_case(
        conn, case_id=case["id"], ruleset_id=case["ruleset_id"], bm_chair=bm_chair, bm_member=bm_member,
    )
    m_row, d_row = cf.verify_adopted(conn, case["id"])
    assert m_row["id"] == motion["id"]
    assert d_row["id"] == decision["id"]


# --------------------------------------------------------------------------- #
# REPAIR (2026-08-23, F-1): a carried GENERIC adoption motion + a recorded
# decision are not, by themselves, proof that every individual standard was
# voted on. render.case_findings._check_no_unresolved_findings() closes
# that gap; these two tests prove it mechanically -- reproducing the exact
# anomaly first, then proving the fix closes it.
# --------------------------------------------------------------------------- #


def test_verify_adopted_refuses_when_a_live_finding_is_still_unresolved(conn):
    """The generic adoption motion carrying, and a decision being recorded,
    is NOT enough on its own -- a live finding node that no motion ever
    concluded (never drafted against, or drafted and then never applied)
    must still block verify_adopted(). Before the repair, this case would
    have passed verify_adopted() cleanly despite node n1 never having been
    voted on at all."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    _insert_finding_node(conn, case_id=case["id"])  # unresolved=1 by column default, never touched
    _adopt_case(conn, case_id=case["id"], ruleset_id=case["ruleset_id"], bm_chair=bm_chair, bm_member=bm_member)
    with pytest.raises(cf.NotAdoptedError, match="still unresolved"):
        cf.verify_adopted(conn, case["id"])


def test_verify_adopted_refuses_when_a_findings_motion_failed_and_was_never_applied(conn):
    """The more realistic shape of the same gap: the Board actually voted
    on the standard, and voted it DOWN. engine.meeting.apply_motion()
    correctly refuses to write a conclusion for a motion that did not
    carry, so the node stays unresolved=1/conclusion=NULL -- exactly like a
    node nobody ever looked at. The generic adoption motion carrying
    afterward must not paper over that."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    _insert_finding_node(conn, case_id=case["id"])
    failed_motion = meeting.draft_node_motion(conn, case_id=case["id"], node_id="n1", actor_user_id=ACTOR)
    voted = meeting.record_vote(
        conn, motion_id=failed_motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=0, votes_no=2, votes_abstain=0, outcome="failed",
        recorded_by=ACTOR, voted_at="2025-12-18T18:15:00.000Z", actor_user_id=ACTOR,
    )
    with pytest.raises(meeting_engine.MotionNotApplicable):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)

    _adopt_case(conn, case_id=case["id"], ruleset_id=case["ruleset_id"], bm_chair=bm_chair, bm_member=bm_member)
    with pytest.raises(cf.NotAdoptedError, match="still unresolved"):
        cf.verify_adopted(conn, case["id"])


# --------------------------------------------------------------------------- #
# render_adopted_final() -- end to end, real PDFs.
# --------------------------------------------------------------------------- #


@requires_toolchain
def test_render_adopted_final_refuses_without_a_real_adoption_vote(conn, tmp_path):
    case = _make_case(conn)
    with pytest.raises(cf.NotAdoptedError):
        cf.render_adopted_final(conn, case["id"], APP_ROOT / "data" / "exports")


@requires_toolchain
def test_render_adopted_final_produces_pdf_md_and_snapshot_with_no_draft_stamp(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    _insert_finding_node(conn, case_id=case["id"])
    _resolve_finding_node(conn, case_id=case["id"], node_id="n1", bm_chair=bm_chair, bm_member=bm_member)
    _adopt_case(conn, case_id=case["id"], ruleset_id=case["ruleset_id"], bm_chair=bm_chair, bm_member=bm_member)

    out_dir = APP_ROOT / "data" / "exports"
    result = cf.render_adopted_final(conn, case["id"], out_dir)
    try:
        assert result.pdf_path.exists() and result.pdf_path.stat().st_size > 0
        assert result.md_path.exists()
        assert result.snapshot_path.exists()

        snapshot = json.loads(result.snapshot_path.read_text())
        assert snapshot["schema"] == "adopted_final_snapshot.v1"
        assert snapshot["content_sha256"] == result.content_sha256
        assert snapshot["decision"]["outcome"] == "approved_with_conditions"
        assert len(snapshot["findings_nodes"]) == 1

        # No DRAFT watermark -- draft=False is threaded through to
        # build-findings.sh (-V draft=true is only ever passed for "on").
        pdf_text = subprocess.run(
            ["pdftotext", str(result.pdf_path), "-"], capture_output=True, text=True,
        ).stdout
        assert "DRAFT" not in pdf_text

        # D-0026: no appeal-rights paragraph is composed anywhere in this
        # pipeline -- reproducing every real sample's omission, on purpose.
        assert "appeal" not in pdf_text.lower() or "Appeal" not in pdf_text

        # D-0028: the certification block's settled (if erroneous) house
        # wording is reproduced verbatim, not corrected.
        assert "Conditions of Law" in pdf_text
    finally:
        result.pdf_path.unlink(missing_ok=True)
        result.md_path.unlink(missing_ok=True)
        result.snapshot_path.unlink(missing_ok=True)


@requires_toolchain
def test_two_renders_of_the_same_tree_and_votes_have_the_same_content_sha_but_the_pdf_bytes_may_differ(conn):
    """THE decisive W7 reproducibility test: same tree + same votes -> same
    content_sha256, proven by actually rendering twice and comparing --
    never asserted from test names. The PDF file's own bytes are NOT
    asserted equal (Typst embeds a wall-clock CreationDate/ModDate into
    every PDF it writes), which is exactly why content_sha256 hashes the
    markdown text, not the PDF."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    _insert_finding_node(conn, case_id=case["id"])
    _resolve_finding_node(conn, case_id=case["id"], node_id="n1", bm_chair=bm_chair, bm_member=bm_member)
    _adopt_case(conn, case_id=case["id"], ruleset_id=case["ruleset_id"], bm_chair=bm_chair, bm_member=bm_member)

    out_dir = APP_ROOT / "data" / "exports"
    r1 = cf.render_adopted_final(conn, case["id"], out_dir)
    r2 = cf.render_adopted_final(conn, case["id"], out_dir)
    try:
        assert r1.content_sha256 == r2.content_sha256
        assert r1.md_path.read_text() == r2.md_path.read_text()
        # Not asserted equal on purpose -- see this test's own docstring.
        # (Left here, commented, as the negative-space proof of why
        # content_sha256 exists at all -- do not uncomment and "fix" this
        # into an equality assertion; that would be asserting something
        # Typst does not actually guarantee.)
        # assert r1.pdf_sha256 == r2.pdf_sha256
    finally:
        for r in (r1, r2):
            r.pdf_path.unlink(missing_ok=True)
            r.md_path.unlink(missing_ok=True)
            r.snapshot_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# downstream_clocks() -- §8.f.1 Clerk filing -> §23.d.1 appeal window.
# No clock arithmetic reimplemented; this only proves the wiring.
# --------------------------------------------------------------------------- #


def test_downstream_clocks_empty_before_any_decision_is_recorded(conn):
    case = _make_case(conn)
    clocks = cf.downstream_clocks(conn, case["id"])
    keys = {d.clock_key: d for d in clocks}
    # decision_filed_with_clerk PENDING_START (no decision_at yet); it still
    # applies to a subdivision case, so it's present but not due.
    assert keys["decision_filed_with_clerk"].due_date is None
    assert keys["administrative_appeal"].due_date is None


def test_decision_issued_starts_the_5_business_day_clerk_filing_clock(conn):
    """A decision recorded 2025-12-18 (Thursday) -> 5 BUSINESS days later
    under the Maine legal-holiday calendar. 2025-12-19 (Fri), 22-23-24
    (Mon-Wed), 25 (Thu, Christmas Day -- a Maine legal holiday, SKIPPED),
    26 (Fri) -> 5th business day = 2025-12-26."""
    case = _make_case(conn)
    cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "decision_issued", "occurred_on": "2025-12-18"}],
        why="Board adopted the findings and decided the application (test fixture).",
        actor_user_id=ACTOR,
    )
    clocks = cf.downstream_clocks(conn, case["id"])
    keys = {d.clock_key: d for d in clocks}

    filing = keys["decision_filed_with_clerk"]
    assert filing.start_date.isoformat() == "2025-12-18"
    assert filing.due_date.isoformat() == "2025-12-26"
    assert filing.status in ("open", "missed")  # not yet satisfied in this fixture

    # The appeal window has not started yet -- no decision_filed_at recorded.
    appeal = keys["administrative_appeal"]
    assert appeal.due_date is None


def test_decision_filed_starts_the_30_calendar_day_appeal_window(conn):
    """Once the Clerk's date stamp (decision_filed) is ALSO recorded, the
    §23.d.1 appeal window computes: 30 CALENDAR days from the filing date,
    2025-12-26 -> 2026-01-25."""
    case = _make_case(conn)
    cases.record_dates(
        conn, case["id"],
        entries=[
            {"kind": "decision_issued", "occurred_on": "2025-12-18"},
            {"kind": "decision_filed", "occurred_on": "2025-12-26"},
        ],
        why="Board decision + Town Clerk filing (test fixture).",
        actor_user_id=ACTOR,
    )
    clocks = cf.downstream_clocks(conn, case["id"])
    keys = {d.clock_key: d for d in clocks}

    filing = keys["decision_filed_with_clerk"]
    assert filing.satisfied_at.isoformat() == "2025-12-26"

    appeal = keys["administrative_appeal"]
    assert appeal.start_date.isoformat() == "2025-12-26"
    assert appeal.due_date.isoformat() == "2026-01-25"
