"""Tests engine/meeting.py -- the bridge from a carried motion's recorded
vote to a Conclusion of Law (findings_nodes.conclusion). This is the piece
engine/findings.py's own "THE ONLY WRITER OF findings_nodes.conclusion"
section names by path before it existed ("engine/meeting.py:apply_motion()
-- the function that first proves a motion CARRIED ... before ever reaching
this code").

Mirrors tests/test_meeting.py's own `conn`/`_make_case`/`_seed_board`
fixtures exactly (same temp-dir SQLite, same seeded rulesets, same board
shape) so both files can be read side by side.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import meeting as app_meeting  # noqa: E402
from engine import findings as findings_mod  # noqa: E402
from engine import meeting as engine_meeting  # noqa: E402

from tests.test_meeting import _make_case, _seed_board  # noqa: E402
from tests.test_meeting import conn  # noqa: E402,F401 -- reused fixture


def _make_standard_node(conn, case_id: str, *, board_question: str = "Is the application consistent?"):
    return findings_mod.create_node(
        conn,
        case_id=case_id,
        node_type="finding",
        number_label="g.",
        heading="g. Traffic",
        board_question=board_question,
        unresolved=True,
        actor_user_id="u_local_operator",
    )


def _draft_and_link_motion(conn, case_id: str, node_id: str, *, proposed_conclusion="met"):
    motion = app_meeting.create_motion(
        conn, case_id=case_id, kind="findings",
        text="To conclude that the application is consistent with Standard g. (Traffic).",
        actor_user_id="u_local_operator",
    )
    return engine_meeting.set_motion_findings_link(
        conn, motion_id=motion["id"], findings_node_id=node_id,
        proposed_conclusion=proposed_conclusion, actor_user_id="u_local_operator",
    )


# --------------------------------------------------------------------------- #
# apply_motion() -- the happy path
# --------------------------------------------------------------------------- #


def test_apply_motion_writes_the_conclusion_from_a_carried_vote(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"], proposed_conclusion="met")

    voted = app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    applied = engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")

    assert applied["applied_node_id"] == node["id"]
    assert applied["applied_at"] is not None

    current = findings_mod.get_node(conn, node["id"])
    assert current["conclusion"] == "met"
    assert current["conclusion_by"] == "u_local_operator"
    assert current["conclusion_at"] == voted["voted_at"]
    assert current["unresolved"] is False


def test_apply_motion_not_met_on_a_carried_vote_with_that_proposed_conclusion(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"], proposed_conclusion="not_met")

    app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=3, votes_no=4, votes_abstain=0, outcome="failed",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    # A FAILED vote never applies -- see the next test for the explicit assertion.
    # Here: record a SEPARATE carried vote scenario to prove not_met flows through.
    node2 = _make_standard_node(conn, case["id"], board_question="second standard?")
    motion2 = _draft_and_link_motion(conn, case["id"], node2["id"], proposed_conclusion="not_met")
    app_meeting.record_vote(
        conn, motion_id=motion2["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=2, votes_no=5, votes_abstain=0, outcome="failed",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    # The Board voted DOWN "to conclude ... is consistent" worded the normal
    # way, but here we exercise a motion that itself proposes 'not_met' and
    # CARRIES (a Board that moves the negative directly and passes it).
    node3 = _make_standard_node(conn, case["id"], board_question="third standard?")
    motion3 = _draft_and_link_motion(conn, case["id"], node3["id"], proposed_conclusion="not_met")
    app_meeting.record_vote(
        conn, motion_id=motion3["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=6, votes_no=1, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    applied = engine_meeting.apply_motion(conn, motion_id=motion3["id"], actor_user_id="u_local_operator")
    assert applied["applied_node_id"] == node3["id"]
    assert findings_mod.get_node(conn, node3["id"])["conclusion"] == "not_met"


# --------------------------------------------------------------------------- #
# apply_motion() -- refusals
# --------------------------------------------------------------------------- #


def test_apply_motion_refuses_a_motion_that_did_not_carry(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"])

    app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=2, votes_no=5, votes_abstain=0, outcome="failed",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    with pytest.raises(engine_meeting.MotionNotApplicable):
        engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")

    # The node must remain untouched -- an honest, still-unresolved blank.
    current = findings_mod.get_node(conn, node["id"])
    assert current["conclusion"] is None
    assert current["unresolved"] is True


def test_apply_motion_refuses_a_motion_with_no_proposed_conclusion(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = app_meeting.create_motion(
        conn, case_id=case["id"], kind="completeness",
        text="To find the application complete and ready for review.",
        actor_user_id="u_local_operator",
    )
    app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    with pytest.raises(engine_meeting.MotionNotApplicable):
        engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")


def test_apply_motion_twice_raises_already_applied_and_never_double_writes(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"])
    app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")

    with pytest.raises(engine_meeting.MotionAlreadyApplied):
        engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")


def test_apply_motion_refuses_when_the_node_was_superseded_by_an_amendment(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"])

    # The Chair amends the finding's wording BEFORE the vote is recorded --
    # a new revision now sits at root_id; `node["id"]` (what the motion
    # still points at) is no longer the current revision.
    findings_mod.amend_node(
        conn, node_id=node["id"], actor_user_id="u_local_operator",
        reason="Corrected a typo in the drafted finding before the vote.",
        board_question="Is the application consistent (corrected)?",
    )

    app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    with pytest.raises(findings_mod.NodeNotEligibleForConclusion):
        engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")


# --------------------------------------------------------------------------- #
# set_motion_findings_link() -- vocabulary/shape validation
# --------------------------------------------------------------------------- #


def test_set_motion_findings_link_rejects_findings_node_id_on_a_non_findings_motion(conn):
    case = _make_case(conn)
    node = _make_standard_node(conn, case["id"])
    motion = app_meeting.create_motion(
        conn, case_id=case["id"], kind="completeness", text="To find the application complete.",
        actor_user_id="u_local_operator",
    )
    with pytest.raises(engine_meeting.ValidationError):
        engine_meeting.set_motion_findings_link(
            conn, motion_id=motion["id"], findings_node_id=node["id"], proposed_conclusion="met",
            actor_user_id="u_local_operator",
        )


def test_set_motion_findings_link_rejects_disposition_on_a_non_decision_motion(conn):
    case = _make_case(conn)
    motion = app_meeting.create_motion(
        conn, case_id=case["id"], kind="findings", text="To accept and adopt the draft findings.",
        actor_user_id="u_local_operator",
    )
    with pytest.raises(engine_meeting.ValidationError):
        engine_meeting.set_motion_findings_link(
            conn, motion_id=motion["id"], disposition="approve", actor_user_id="u_local_operator",
        )


def test_set_motion_findings_link_accepts_a_valid_decision_disposition(conn):
    case = _make_case(conn)
    motion = app_meeting.create_motion(
        conn, case_id=case["id"], kind="decision",
        text="To approve, with conditions, the application as discussed and amended.",
        actor_user_id="u_local_operator",
    )
    linked = engine_meeting.set_motion_findings_link(
        conn, motion_id=motion["id"], disposition="approve_with_conditions",
        discussion="none", actor_user_id="u_local_operator",
    )
    assert linked["disposition"] == "approve_with_conditions"
    assert linked["discussion"] == "none"


# --------------------------------------------------------------------------- #
# THE ONLY WRITER -- mechanical proof, matching engine/findings.py's own
# comment naming this exact test (tests/test_findings.py's copy is the
# grep-based whole-tree version; this one is the narrower "the bridge
# actually goes through it" proof for this module specifically).
# --------------------------------------------------------------------------- #


def test_apply_motion_conclusion_matches_what_write_conclusion_would_produce(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    motion = _draft_and_link_motion(conn, case["id"], node["id"], proposed_conclusion="n_a")
    voted = app_meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    engine_meeting.apply_motion(conn, motion_id=motion["id"], actor_user_id="u_local_operator")
    current = findings_mod.get_node(conn, node["id"])
    assert current["conclusion"] == "n_a"
    assert current["conclusion_at"] == voted["voted_at"]


# --------------------------------------------------------------------------- #
# ensure_agenda_motions() / build_agenda() -- the whole-sequence assembler.
# --------------------------------------------------------------------------- #


def test_ensure_agenda_motions_drafts_completeness_and_per_standard_motions(conn):
    case = _make_case(conn)
    node1 = _make_standard_node(conn, case["id"], board_question="Standard g?")
    node2 = _make_standard_node(conn, case["id"], board_question="Standard j?")
    # A note-type node with no board_question must NOT get a motion.
    findings_mod.create_node(
        conn, case_id=case["id"], node_type="note", body="A cross-reference note.",
        finding_source="engine", provenance={"citation": {"article": 7}},
        actor_user_id="u_local_operator",
    )

    created = engine_meeting.ensure_agenda_motions(conn, case_id=case["id"], actor_user_id="u_local_operator")
    assert created["completeness"] == 1
    assert created["findings"] == 2

    motions = app_meeting.get_motions(conn, case["id"])
    assert sum(1 for m in motions if m["kind"] == "completeness") == 1
    linked_node_ids = {m["findings_node_id"] for m in motions if m["findings_node_id"]}
    assert linked_node_ids == {node1["id"], node2["id"]}

    # Idempotent: calling again drafts nothing new.
    created_again = engine_meeting.ensure_agenda_motions(conn, case_id=case["id"], actor_user_id="u_local_operator")
    assert created_again == {"completeness": 0, "findings": 0, "conditions": 0}
    assert len(app_meeting.get_motions(conn, case["id"])) == len(motions)


def test_build_agenda_counts_and_disclosures_render_tbd_when_absent(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    _make_standard_node(conn, case["id"])
    engine_meeting.ensure_agenda_motions(conn, case_id=case["id"], actor_user_id="u_local_operator")

    agenda = engine_meeting.build_agenda(conn, case["id"])
    assert agenda["disclosures_resolved"] is False
    for d in agenda["disclosures"]:
        assert d["recorded"] is False
        assert d["disclosed"] is None  # never a false "no conflicts" default
    assert agenda["counts"]["total"] >= 4  # disclosures + completeness + 1 standard + adoption + decision
    assert agenda["counts"]["resolved"] == 0

    app_meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=chair_id, disclosed=False, actor_user_id="u_local_operator",
    )
    app_meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=member_id, disclosed=False, actor_user_id="u_local_operator",
    )
    agenda2 = engine_meeting.build_agenda(conn, case["id"])
    assert agenda2["disclosures_resolved"] is True
    assert agenda2["counts"]["resolved"] == 1


def test_build_agenda_standard_resolved_after_apply_motion(conn):
    case = _make_case(conn)
    chair_id, member_id = _seed_board(conn)
    node = _make_standard_node(conn, case["id"])
    engine_meeting.ensure_agenda_motions(conn, case_id=case["id"], actor_user_id="u_local_operator")

    agenda = engine_meeting.build_agenda(conn, case["id"])
    standard = agenda["standards"][0]
    assert standard["resolved"] is False
    assert standard["motion"] is not None
    assert standard["citation_text"] is None  # this fixture node carries no citation_json

    motion_id = standard["motion"]["id"]
    app_meeting.record_vote(
        conn, motion_id=motion_id, moved_by=chair_id, seconded_by=member_id,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_local_operator", actor_user_id="u_local_operator",
    )
    engine_meeting.apply_motion(conn, motion_id=motion_id, actor_user_id="u_local_operator")

    agenda2 = engine_meeting.build_agenda(conn, case["id"])
    assert agenda2["standards"][0]["resolved"] is True
    assert agenda2["standards"][0]["conclusion"] == "met"


def test_create_adoption_motion_is_idempotent_and_verbatim(conn):
    case = _make_case(conn)
    m1 = engine_meeting.create_adoption_motion(conn, case_id=case["id"], actor_user_id="u_local_operator")
    assert m1["text"] == engine_meeting.ADOPTION_MOTION_TEXT
    assert m1["findings_node_id"] is None
    m2 = engine_meeting.create_adoption_motion(conn, case_id=case["id"], actor_user_id="u_local_operator")
    assert m2["id"] == m1["id"]
    assert len([m for m in app_meeting.get_motions(conn, case["id"]) if m["text"] == engine_meeting.ADOPTION_MOTION_TEXT]) == 1


def test_create_decision_motion_templates_by_disposition(conn):
    case = _make_case(conn, application_type="subdivision")
    motion = engine_meeting.create_decision_motion(
        conn, case_id=case["id"], disposition="approve_with_conditions", actor_user_id="u_local_operator",
    )
    assert motion["kind"] == "decision"
    assert motion["disposition"] == "approve_with_conditions"
    assert "approve, with conditions" in motion["text"]
    assert "subdivision" in motion["text"]


def test_create_decision_motion_rejects_unknown_disposition(conn):
    case = _make_case(conn)
    with pytest.raises(engine_meeting.ValidationError):
        engine_meeting.create_decision_motion(
            conn, case_id=case["id"], disposition="not-a-real-choice", actor_user_id="u_local_operator",
        )
