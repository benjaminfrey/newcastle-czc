"""A conclusion must trace to a carried motion — the reverse direction the
CHECK constraint cannot enforce.

0013_findings_tree.sql guarantees a conclusion is ATTRIBUTED:

    CHECK (conclusion IS NULL OR (conclusion_by IS NOT NULL AND conclusion_at IS NOT NULL))

and 0015/0016 make the `motions` side tight (`applied_node_id` write-once,
settable only on a carried motion carrying a `proposed_conclusion`), so a
motion cannot claim an application it never made.

Neither can express the cross-table fact that a CONCLUSION has a MOTION behind
it. These tests cover that gap.

Found 2026-08-24 by attacking the W7 build directly: of four forgery attempts
against `findings_nodes.conclusion`, three were blocked by the CHECK and the
fourth — a fully attributed conclusion with no motion — succeeded, wrote no
`events` row (so the hash chain still verified), and was invisible to every
check the app ran. It would have printed in an adopted document as though the
Board had voted it.

The likelier real-world cause is not tampering but a future code path that sets
a conclusion without going through apply_motion(); this is primarily a
regression guard against that.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from app import cases, db, security  # noqa: E402
from engine import criteria_seed, findings, subdivision_review  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ADOPTED_ID = "r_adopted"
ACTOR = security.SYNTHETIC_USER_ID
NOW = "2026-08-24T00:00:00.000Z"


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    c.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'adopted', 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'ruleset_build/1.0.0', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (ADOPTED_ID, NOW, NOW),
    )
    yield c
    c.close()


@pytest.fixture()
def walked(conn):
    """A subdivision case with the full 21-standard walk and no conclusions."""
    seeded = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR
    )
    case = cases.create_case(
        conn, application_type="subdivision", map_lot="M-ORPHAN", situs_address="Test Rd",
        applicant_name="Test Applicant", actor_user_id=ACTOR,
    )
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    subdivision_review.run_walk(
        conn, case_id=case["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
        facts={}, default_ruleset_key="adopted", actor_user_id=ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )
    return case


def _a_finding_node_id(conn: sqlite3.Connection, case_id: str) -> str:
    row = conn.execute(
        "SELECT id FROM findings_nodes WHERE case_id = ? AND node_type = 'finding' "
        "ORDER BY sort_order LIMIT 1;",
        (case_id,),
    ).fetchone()
    assert row is not None
    return row["id"]


# --------------------------------------------------------------------------- #
# The direction that already worked: the CHECK blocks an UNATTRIBUTED conclusion
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("label", "sql", "extra"),
    [
        ("no attribution at all",
         "UPDATE findings_nodes SET conclusion='met' WHERE id=?", ()),
        ("named human, but no time",
         "UPDATE findings_nodes SET conclusion='met', conclusion_by=? WHERE id=?", (ACTOR,)),
        ("a time, but nobody named",
         "UPDATE findings_nodes SET conclusion='met', conclusion_at=? WHERE id=?", (NOW,)),
    ],
)
def test_the_check_constraint_blocks_an_unattributed_conclusion(
    conn, walked, label: str, sql: str, extra: tuple
) -> None:
    node_id = _a_finding_node_id(conn, walked["id"])
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, (*extra, node_id))


# --------------------------------------------------------------------------- #
# The gap: FULLY ATTRIBUTED, but no motion behind it
# --------------------------------------------------------------------------- #


def test_a_fully_attributed_conclusion_with_no_motion_is_detected(conn, walked) -> None:
    """The forgery the CHECK cannot see. It must not pass silently."""
    node_id = _a_finding_node_id(conn, walked["id"])
    assert findings.find_orphan_conclusions(conn, walked["id"]) == []

    # Exactly the write that succeeded against the W7 build: correct shape,
    # correct attribution, no vote anywhere behind it. Note it deliberately
    # writes no `events` row -- that is the point: the hash chain detects
    # tampering with the LOG, not divergence between the log and the state.
    conn.execute(
        "UPDATE findings_nodes SET conclusion='met', conclusion_by=?, conclusion_at=? "
        "WHERE id=?;",
        (ACTOR, NOW, node_id),
    )
    conn.commit()

    orphans = findings.find_orphan_conclusions(conn, walked["id"])
    assert len(orphans) == 1, "a conclusion with no carried motion must be reported"
    assert orphans[0]["id"] == node_id
    assert orphans[0]["conclusion"] == "met"

    with pytest.raises(findings.OrphanConclusionError) as exc:
        findings.assert_no_orphan_conclusions(conn, walked["id"])
    # The message must name the standard and the claimed decider, so a reader
    # can go look at the record rather than just being told something is wrong.
    assert "no carried motion" in str(exc.value)
    assert ACTOR in str(exc.value)


def test_the_audit_chain_alone_does_not_catch_it(conn, walked) -> None:
    """Why this check has to exist at all.

    A direct UPDATE writes no `events` row, so the append-only hash chain is
    untouched and still verifies. Chain integrity is not record integrity.
    """
    from app import audit

    node_id = _a_finding_node_id(conn, walked["id"])
    conn.execute(
        "UPDATE findings_nodes SET conclusion='met', conclusion_by=?, conclusion_at=? "
        "WHERE id=?;",
        (ACTOR, NOW, node_id),
    )
    conn.commit()

    ok, _bad_seq = audit.verify_chain(conn)
    assert ok is True, "the chain still verifies -- which is exactly the problem"
    assert findings.find_orphan_conclusions(conn, walked["id"]), (
        "so the orphan check, not the chain, is what must catch this"
    )


# --------------------------------------------------------------------------- #
# The other direction: a sound record must stay silent
# --------------------------------------------------------------------------- #


def test_a_clean_walk_reports_no_orphans(conn, walked) -> None:
    """No conclusions at all -- the W6 state -- is a sound record, not an error."""
    assert findings.find_orphan_conclusions(conn, walked["id"]) == []
    findings.assert_no_orphan_conclusions(conn, walked["id"])  # must not raise


def _a_board_member(conn: sqlite3.Connection) -> str:
    """motions.moved_by/seconded_by reference board_members(id), NOT users(id) --
    a motion is moved by a member of the Board, not by whoever is at the keyboard."""
    conn.execute(
        "INSERT INTO board_members (id, user_id, seat, is_alternate, is_chair, "
        "term_start, term_end, created_at, actor_user_id) "
        "VALUES ('bm_1', ?, 'Seat 1', 0, 1, '2026-01-01', NULL, ?, ?);",
        (ACTOR, NOW, ACTOR),
    )
    return "bm_1"


def test_a_conclusion_with_a_carried_motion_is_not_an_orphan(conn, walked) -> None:
    """The legitimate path: a carried motion pointing at the node it concluded."""
    node_id = _a_finding_node_id(conn, walked["id"])
    member = _a_board_member(conn)
    conn.execute(
        """
        INSERT INTO motions
            (id, case_id, sort_order, kind, text, moved_by, seconded_by,
             votes_yes, votes_no, votes_abstain, outcome, voted_at, recorded_by,
             created_at, actor_user_id, findings_node_id, proposed_conclusion,
             applied_node_id, applied_at)
        VALUES ('m_ok', ?, 1, 'findings', 'That the Board find standard a. met.',
                ?, ?, 3, 0, 0, 'carried', ?, ?, ?, ?, ?, 'met', ?, ?);
        """,
        (walked["id"], member, member, NOW, ACTOR, NOW, ACTOR, node_id, node_id, NOW),
    )
    conn.execute(
        "UPDATE findings_nodes SET conclusion='met', conclusion_by=?, conclusion_at=? "
        "WHERE id=?;",
        (ACTOR, NOW, node_id),
    )
    conn.commit()

    assert findings.find_orphan_conclusions(conn, walked["id"]) == []
    findings.assert_no_orphan_conclusions(conn, walked["id"])  # must not raise


def test_a_failed_motion_does_not_launder_a_conclusion(conn, walked) -> None:
    """A motion that did NOT carry cannot stand behind a conclusion.

    0015's own CHECK already refuses `applied_node_id` on a non-carried motion,
    so the laundering attempt is blocked at the write. If that constraint ever
    loosened, the orphan query's `outcome = 'carried'` clause is the backstop.
    """
    node_id = _a_finding_node_id(conn, walked["id"])
    member = _a_board_member(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO motions
                (id, case_id, sort_order, kind, text, moved_by, seconded_by,
                 votes_yes, votes_no, votes_abstain, outcome, voted_at, recorded_by,
                 created_at, actor_user_id, findings_node_id, proposed_conclusion,
                 applied_node_id, applied_at)
            VALUES ('m_failed', ?, 2, 'findings', 'That the Board find standard a. met.',
                    ?, ?, 1, 4, 0, 'failed', ?, ?, ?, ?, ?, 'met', ?, ?);
            """,
            (walked["id"], member, member, NOW, ACTOR, NOW, ACTOR, node_id, node_id, NOW),
        )


def test_orphans_are_found_across_the_whole_database_when_unscoped(conn, walked) -> None:
    """`case_id=None` sweeps every case, which is what --selftest check 11 does."""
    node_id = _a_finding_node_id(conn, walked["id"])
    conn.execute(
        "UPDATE findings_nodes SET conclusion='n_a', conclusion_by=?, conclusion_at=? "
        "WHERE id=?;",
        (ACTOR, NOW, node_id),
    )
    conn.commit()
    assert len(findings.find_orphan_conclusions(conn)) == 1
