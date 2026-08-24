"""Tests the W7 "motions, votes, and amendments -- the ONLY path to a
conclusion" task.

Two modules, reconciled mid-build with a concurrently-running sibling W7
session (same shape of collision BUILD-STATE.md's W5 section and
0013_findings_tree.sql's own header each document once already -- see
app/meeting.py's and engine/meeting.py's own reconciliation notes):

  - app/meeting.py:draft_node_motion(s)/draft_text_for_node() -- DRAFT a
    motion, prefilled from a findings_nodes row, text and proposed
    conclusion both composed here, vote fields NULL.
  - engine/meeting.py:apply_motion() -- THE ONLY caller of
    engine/findings.py's `_write_conclusion()`, THE ONLY raw UPDATE in the
    whole application that can ever set findings_nodes.conclusion. Reachable
    only after a motion has genuinely CARRIED.

THE CORE CLAIM under test: there is no code path -- the review engine, an
import, a migration, or a render -- by which findings_nodes.conclusion is
ever set except engine.meeting.apply_motion() applying a CARRIED motion.
Every test above the "THE PROOF" section exercises one guard of that
function; the two tests in "THE PROOF" prove the claim mechanically, by
grepping the actual source tree for real call sites (not docstring prose
mentioning the function's name), not by enumerating call sites from memory.

Offline, throwaway temp-dir SQLite -- mirrors tests/test_meeting.py's and
tests/test_findings.py's own `conn`/`_seed_board` fixtures exactly (both
already established this exact pattern; duplicated here rather than
imported, matching this test suite's own convention of small per-file
fixtures over a shared conftest).
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, cases, db, meeting, security  # noqa: E402
from app.citation import Citation  # noqa: E402
from engine import findings  # noqa: E402
from engine import meeting as meeting_engine  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID


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


def _seed_board(conn) -> tuple[str, str]:
    """Chair + one member. Returns (chair_board_member_id, member_board_member_id)."""
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_chair', 'Ben Frey', 'chair', '2026-08-23T00:00:00.000Z'), "
        "('u_member', 'Lucas Kostenbader', 'board_member', '2026-08-23T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, is_chair, term_start, created_at) VALUES "
        "('bm_chair', 'u_chair', 1, '2026-01-01', '2026-08-23T00:00:00.000Z'), "
        "('bm_member', 'u_member', 0, '2026-01-01', '2026-08-23T00:00:00.000Z');"
    )
    return "bm_chair", "bm_member"


CITATION = Citation(ruleset_key="adopted", scheme="adopted", article=7, section="12", subsection="d")

STANDARD_TEXT = (
    "The proposed subdivision has sufficient water available for the reasonably "
    "foreseeable needs of the subdivision."
)


def _seed_finding_node(conn, case_id, *, applicability_verdict="true", **overrides) -> dict:
    kwargs = dict(
        case_id=case_id,
        node_type="finding",
        number_label="d.",
        heading="d. Sufficient Water",
        quoted_standard_text=STANDARD_TEXT,
        body="Existing conditions do not indicate insufficient water for expected future development.",
        finding_source="engine",
        citation=CITATION,
        applicability_verdict=applicability_verdict,
        unresolved=True,
        provenance={"rule_id": "rule_water", "citation": {"article": 7, "section": "12", "subsection": "d"}},
        actor_user_id=ACTOR,
    )
    kwargs.update(overrides)
    return findings.create_node(conn, **kwargs)


# --------------------------------------------------------------------------- #
# draft_text_for_node() -- the prefill template
# --------------------------------------------------------------------------- #


def test_draft_text_for_applicable_node_proposes_met(conn):
    case = _make_case(conn)
    node = _seed_finding_node(conn, case["id"], applicability_verdict="true")
    text, proposed = meeting.draft_text_for_node(node)
    assert proposed == "met"
    assert text.startswith("To conclude that the application is consistent with")
    assert "Section 12" in text


def test_draft_text_for_not_applicable_node_proposes_n_a(conn):
    case = _make_case(conn)
    node = _seed_finding_node(
        conn, case["id"], applicability_verdict="false",
        body="The standard set forth under Article 7 do not address, and therefore do not apply to, this application.",
    )
    text, proposed = meeting.draft_text_for_node(node)
    assert proposed == "n_a"
    assert "not applicable" in text


# --------------------------------------------------------------------------- #
# draft_node_motion(s) -- prefilled, blank vote slots, idempotent
# --------------------------------------------------------------------------- #


def test_draft_node_motion_creates_blank_findings_motion(conn):
    case = _make_case(conn)
    node = _seed_finding_node(conn, case["id"])

    motion = meeting.draft_node_motion(conn, case_id=case["id"], node_id=node["id"], sort_order=100, actor_user_id=ACTOR)

    assert motion["kind"] == "findings"
    assert motion["findings_node_id"] == node["id"]
    assert motion["proposed_conclusion"] == "met"
    assert motion["text"]
    # Blank vote slots -- matches create_motion()'s own convention.
    assert motion["moved_by"] is None
    assert motion["seconded_by"] is None
    assert motion["outcome"] is None
    assert motion["applied_node_id"] is None
    assert motion["applied_at"] is None

    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'motions' AND entity_id = ? ORDER BY seq;", (motion["id"],)
    ).fetchall()
    # create_motion() + set_motion_findings_link() -- two writes, two events,
    # composed rather than a third INSERT path (see app/meeting.py's own
    # reconciliation note on draft_node_motion()).
    assert [e["kind"] for e in events] == ["motion.created", "motion.linked"]
    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"chain broken at seq={bad_seq}"


def test_draft_node_motion_refuses_a_node_that_already_has_a_conclusion(conn):
    case = _make_case(conn)
    node = _seed_finding_node(conn, case["id"])
    conn.execute("BEGIN;")
    findings._write_conclusion(conn, node_id=node["id"], conclusion="met", conclusion_by=ACTOR, conclusion_at="2026-08-23T00:00:00.000Z")
    conn.execute("COMMIT;")

    with pytest.raises(ValueError):
        meeting.draft_node_motion(conn, case_id=case["id"], node_id=node["id"], actor_user_id=ACTOR)


def test_draft_node_motions_drafts_one_per_eligible_node_and_skips_the_rest(conn):
    case = _make_case(conn)
    node_a = _seed_finding_node(conn, case["id"], number_label="a.", heading="a. Standards of this Code")
    node_b = _seed_finding_node(conn, case["id"], number_label="b.", heading="b. RDEO", applicability_verdict="false")
    # A section node (not finding/conclusion) -- never eligible.
    findings.create_node(conn, case_id=case["id"], node_type="section", heading="Subdivision Standards", actor_user_id=ACTOR)

    drafted = meeting.draft_node_motions(conn, case_id=case["id"], actor_user_id=ACTOR, sort_start=100)
    assert {m["findings_node_id"] for m in drafted} == {node_a["id"], node_b["id"]}
    assert {m["proposed_conclusion"] for m in drafted} == {"met", "n_a"}

    # Idempotent: calling again drafts nothing new.
    again = meeting.draft_node_motions(conn, case_id=case["id"], actor_user_id=ACTOR, sort_start=200)
    assert again == []

    all_motions = meeting.get_motions(conn, case["id"])
    assert len(all_motions) == 2


# --------------------------------------------------------------------------- #
# engine.meeting.apply_motion() -- THE ONLY PATH TO findings_nodes.conclusion
# --------------------------------------------------------------------------- #


def _draft_and_carry(conn, case_id, node, *, bm_chair, bm_member, outcome="carried", recorded_by=ACTOR, voted_at="2026-08-23T18:45:00.000Z"):
    motion = meeting.draft_node_motion(conn, case_id=case_id, node_id=node["id"], actor_user_id=ACTOR)
    return meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome=outcome,
        recorded_by=recorded_by, voted_at=voted_at, actor_user_id=ACTOR,
    )


def test_apply_motion_sets_conclusion_from_the_motions_own_recorded_by_and_voted_at(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    node = _seed_finding_node(conn, case["id"])

    voted = _draft_and_carry(conn, case["id"], node, bm_chair=bm_chair, bm_member=bm_member, recorded_by="u_chair", voted_at="2026-08-23T18:45:12.345Z")
    assert voted["outcome"] == "carried"
    assert voted["applied_node_id"] is None  # carried != applied yet

    concluded = meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)
    assert concluded["applied_node_id"] == node["id"]

    node_after = findings.get_node(conn, node["id"])
    assert node_after["conclusion"] == "met"
    # conclusion_by/conclusion_at come from the MOTION's recorded_by/voted_at,
    # NOT from actor_user_id and NOT from "now" -- the W7 brief's own words.
    assert node_after["conclusion_by"] == "u_chair"
    assert node_after["conclusion_at"] == "2026-08-23T18:45:12.345Z"
    assert node_after["unresolved"] is False

    motion_after = conn.execute("SELECT * FROM motions WHERE id = ?;", (voted["id"],)).fetchone()
    assert motion_after["applied_node_id"] == node["id"]
    assert motion_after["applied_at"] is not None

    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'findings_nodes' AND entity_id = ? ORDER BY seq;",
        (node["id"],),
    ).fetchall()
    assert [e["kind"] for e in events] == ["findings_node.created", "motion.applied"]
    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"chain broken at seq={bad_seq}"


@pytest.mark.parametrize("outcome", ["failed", "tabled", "withdrawn"])
def test_apply_motion_refuses_any_outcome_that_is_not_carried(conn, outcome):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    node = _seed_finding_node(conn, case["id"])
    voted = _draft_and_carry(conn, case["id"], node, bm_chair=bm_chair, bm_member=bm_member, outcome=outcome)

    with pytest.raises(meeting_engine.MotionNotApplicable):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)

    reloaded = findings.get_node(conn, node["id"])
    assert reloaded["conclusion"] is None
    assert reloaded["unresolved"] is True


def test_apply_motion_refuses_an_unvoted_motion(conn):
    case = _make_case(conn)
    node = _seed_finding_node(conn, case["id"])
    motion = meeting.draft_node_motion(conn, case_id=case["id"], node_id=node["id"], actor_user_id=ACTOR)

    with pytest.raises(meeting_engine.MotionNotApplicable):
        meeting_engine.apply_motion(conn, motion_id=motion["id"], actor_user_id=ACTOR)

    assert findings.get_node(conn, node["id"])["conclusion"] is None


def test_apply_motion_refuses_to_apply_twice(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    node = _seed_finding_node(conn, case["id"])
    voted = _draft_and_carry(conn, case["id"], node, bm_chair=bm_chair, bm_member=bm_member)

    meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)
    with pytest.raises(meeting_engine.MotionAlreadyApplied):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)

    # A second attempt did not write a second events row.
    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'findings_nodes' AND entity_id = ? ORDER BY seq;",
        (node["id"],),
    ).fetchall()
    assert [e["kind"] for e in events] == ["findings_node.created", "motion.applied"]


def test_apply_motion_refuses_a_motion_with_no_findings_node(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    completeness = meeting.create_motion(
        conn, case_id=case["id"], kind="completeness",
        text="To find the application to be complete.", actor_user_id=ACTOR,
    )
    voted = meeting.record_vote(
        conn, motion_id=completeness["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_chair", actor_user_id=ACTOR,
    )
    with pytest.raises(meeting_engine.MotionNotApplicable):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)


def test_apply_motion_refuses_the_verbatim_adoption_motion_shape(conn):
    """The whole-document adoption motion ('To accept and adopt the draft
    findings of fact and conclusions of law, as amended.') is a kind='findings'
    motion with NO findings_node_id -- exactly the shape apply_motion() must
    also refuse, since it concludes nothing about any one node by itself."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    adoption = meeting.create_motion(
        conn, case_id=case["id"], kind="findings",
        text="To accept and adopt the draft findings of fact and conclusions of law, as amended.",
        actor_user_id=ACTOR,
    )
    voted = meeting.record_vote(
        conn, motion_id=adoption["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_chair", actor_user_id=ACTOR,
    )
    with pytest.raises(meeting_engine.MotionNotApplicable):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)


def test_apply_motion_refuses_a_stale_node_amended_after_the_motion_was_drafted(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    node = _seed_finding_node(conn, case["id"])
    motion = meeting.draft_node_motion(conn, case_id=case["id"], node_id=node["id"], actor_user_id=ACTOR)

    # The node gets amended (a real revision, with a real why) BEFORE the vote.
    findings.amend_node(
        conn, node_id=node["id"], actor_user_id=ACTOR,
        reason="Board member corrected a citation before the vote",
        body="Corrected finding text.",
    )

    voted = meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=7, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by="u_chair", actor_user_id=ACTOR,
    )
    # The motion still points at the now-superseded revision -- apply_motion()
    # must refuse rather than writing a conclusion onto a stale row.
    with pytest.raises(findings.NodeNotEligibleForConclusion):
        meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)


def test_apply_motion_unknown_motion_id_raises(conn):
    with pytest.raises(meeting_engine.MotionNotFound):
        meeting_engine.apply_motion(conn, motion_id="does-not-exist", actor_user_id=ACTOR)


# --------------------------------------------------------------------------- #
# THE PROOF: enumerate the writers of findings_nodes.conclusion mechanically.
# --------------------------------------------------------------------------- #

_SOURCE_DIRS = ("app", "engine", "render", "ingest", "llm", "ruleset_build")
_CONCLUSION_WRITE_RE = re.compile(r"SET\s+conclusion\s*=", re.IGNORECASE)
_WRITER_MENTION_RE = re.compile(r"_write_conclusion\s*\(")


def _iter_source_files():
    for d in _SOURCE_DIRS:
        base = REPO_ROOT / d
        if not base.is_dir():
            continue
        yield from base.rglob("*.py")


def test_conclusion_has_exactly_one_writer_in_the_whole_tree():
    """Grep the ACTUAL application source (never migrations, never tests)
    for every literal 'SET conclusion =' -- SQLite's own column-assignment
    syntax -- and prove there is exactly one, in engine/findings.py's
    `_write_conclusion()`. This is the mechanical version of "no code path
    can set a conclusion without a recorded motion behind it": if a second
    writer is ever added anywhere in app/, engine/, render/, ingest/, llm/,
    or ruleset_build/, this test fails the build.
    """
    hits: list[tuple[Path, int, str]] = []
    for path in _iter_source_files():
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            if _CONCLUSION_WRITE_RE.search(line):
                hits.append((path.relative_to(REPO_ROOT), i, line.strip()))

    assert len(hits) == 1, (
        f"expected exactly one 'SET conclusion =' in the application source, found {len(hits)}: {hits}"
    )
    only_path, _line_no, _text = hits[0]
    assert only_path == Path("engine/findings.py"), (
        f"the sole conclusion writer moved out of engine/findings.py to {only_path} -- "
        "update this test deliberately if that was an intended relocation, "
        "never silence it by loosening the assertion"
    )


def _is_real_call(line: str) -> bool:
    """True if `line` contains an actual CALL to _write_conclusion(...) --
    i.e. the open paren is followed by real argument text or a line break --
    as opposed to a bare doc/comment MENTION of the name written as
    `_write_conclusion()` with empty parens (this codebase's own consistent
    style for referring to a function by name in prose, verified against
    every real occurrence in engine/findings.py and engine/meeting.py at the
    time this test was written: every real call spans multiple lines
    starting with `conn,` as its first argument; every empty-parens
    `_write_conclusion()` in this tree is a prose mention, in a docstring or
    a `#` comment)."""
    m = _WRITER_MENTION_RE.search(line)
    if not m:
        return False
    after = line[m.end():].lstrip()
    return not after.startswith(")")  # "_write_conclusion()" (empty) -> a mention, not a call


def test_write_conclusion_has_exactly_one_caller_in_the_whole_tree():
    """Grep for every REAL call to `_write_conclusion(...)` (see
    `_is_real_call()`'s own docstring for how a bare prose mention like
    "the function `_write_conclusion()`" is told apart from an actual call)
    and prove there is exactly one, and that it lives inside
    engine/meeting.py:apply_motion() -- the function that has already
    proven the motion CARRIED before ever reaching it."""
    call_sites: list[tuple[Path, int]] = []
    for path in _iter_source_files():
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(REPO_ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            if rel == Path("engine/findings.py") and line.strip().startswith("def "):
                continue  # the definition itself
            if _is_real_call(line):
                call_sites.append((rel, i))

    assert len(call_sites) == 1, f"expected exactly one caller of _write_conclusion(), found {call_sites}"
    only_path, call_line = call_sites[0]
    assert only_path == Path("engine/meeting.py")

    # And that one call site is textually inside apply_motion(), not some
    # other function in the same file (walk backward from the call site to
    # the nearest preceding top-level `def`).
    meeting_src = (REPO_ROOT / "engine" / "meeting.py").read_text(encoding="utf-8").splitlines()
    enclosing_def = None
    for i in range(call_line - 1, -1, -1):
        line = meeting_src[i]
        if line.startswith("def "):
            enclosing_def = line
            break
    assert enclosing_def is not None and enclosing_def.startswith("def apply_motion("), (
        f"_write_conclusion() is called from {enclosing_def!r}, not apply_motion()"
    )


def test_apply_motion_is_the_only_function_that_can_reach_the_writer_after_a_real_vote(conn):
    """An end-to-end restatement of the two grep-based proofs above, run
    against a live database: starting from an unresolved node, the ONLY
    sequence of public calls that ends with conclusion set is
    draft -> vote(outcome='carried') -> apply_motion(). Every other
    reachable combination (draft alone, draft+vote(failed), draft+vote+
    apply twice) leaves conclusion NULL or raises -- exercised individually
    above; this test is the "and here it is happening" version."""
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    node = _seed_finding_node(conn, case["id"])
    assert findings.get_node(conn, node["id"])["conclusion"] is None

    voted = _draft_and_carry(conn, case["id"], node, bm_chair=bm_chair, bm_member=bm_member)
    assert findings.get_node(conn, node["id"])["conclusion"] is None  # carried, not yet applied

    meeting_engine.apply_motion(conn, motion_id=voted["id"], actor_user_id=ACTOR)
    assert findings.get_node(conn, node["id"])["conclusion"] == "met"
