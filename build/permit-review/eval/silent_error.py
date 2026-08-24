"""eval/silent_error.py -- the REAL silent_error_rate: measured where a wrong
value can genuinely reach RENDERED OUTPUT unflagged.

--------------------------------------------------------------------------
WHY eval/metrics.py's silent_error_rate (over field_candidates) IS RIGHT TO
BE 0, AND WRONG AS *THE* SILENT-ERROR METRIC
--------------------------------------------------------------------------
`ingest/fields.py:FieldCandidate.__post_init__` raises unless
`needs_confirmation is True` -- there is no code path in this codebase that
can construct an unflagged candidate. That invariant is a real safety
property and this module does not touch it, weaken it, or add an escape
hatch to it. But it also means eval.metrics.fact_fidelity_and_silent_error's
`ungrounded_and_unflagged` counter is measuring a branch that is provably
dead code (`elif not cand.needs_confirmation:` can never execute) -- the
number it prints (0.0000, always) says nothing about the app's actual
safety, because the layer it watches cannot fail.

`field_values` cannot silently carry a wrong value either: every write path
in `app/extraction.py` (`confirm_field`, `override_field`,
`mark_not_applicable`) requires a real `actor_user_id`, and the DB's own
CHECK constraints (0001_init.sql) refuse `state='confirmed'` without
`confirmed_by` and refuse `state='overridden'` without `override_reason`
AND `confirmed_by`. A field_values row is always a human's explicit act,
attributed and reasoned -- not the app being silently wrong.

--------------------------------------------------------------------------
THE LAYER WHERE A SILENT ERROR IS GENUINELY POSSIBLE
--------------------------------------------------------------------------
`engine/subdivision_review.py:run_walk()` dispatches each of the 21
subdivision standards through `engine/applicability.py:gate_one()` against a
plain, unprovenanced `facts: dict[str, Any]` the caller supplies. Read
`engine/subdivision_review.py`'s own comment on the `unresolved=True` it
writes to every findings_nodes row (verbatim, because it corrects an
over-broad first read of it): the DB-level `unresolved` column is ALWAYS 1
for a 'finding' node until a human votes -- that column means "not yet
concluded by the Board", not "flagged for a second look". The thing a
reader of the rendered PDF actually SEES is different: whether the node
prints with a highlighted `#boardq[...]` / `#unresolved[...]` box
(render/findings-template.typ) or only a plain italic `#finding[...]`
paragraph (render/case_findings.py:`_finding_node_to_render_nodes()`,
render/findings_to_md.py).

Every fact-bearing disposition this engine can produce PAIRS its stated
fact with a highlighted board_question, by construction:
  - numeric/boolean FACT_RECORDED (engine/review.py:evaluate_numeric_
    criterion / the boolean branch in engine/subdivision_review.py:
    _dispatch_true) -- unresolved=True, board_question ALWAYS set.
  - judgement / applicability-UNKNOWN -- BOARD_QUESTION disposition,
    board_question ALWAYS set.
EXCEPT ONE: applicability verdict FALSE -> NOT_APPLICABLE
(engine/review.py:evaluate_not_applicable) sets `body` (a declarative "does
not apply" sentence) and `board_question=None`. Rendered
(_finding_node_to_render_nodes), that produces ONLY a `#finding[...]`
paragraph -- no `#boardq`, no `#unresolved` -- visually IDENTICAL to a
finding a human already reviewed. The applicability verdict itself is
computed by `engine/predicates.py:evaluate()` against `facts` for exactly
4 of the 21 standards (l, n, r, t -- the only ones whose Code text embeds a
real conditional; read live from the built ruleset by
`fact_dependent_rules()` below, not hardcoded). Nothing about `facts` today
ties a value to field_values' human-confirmation state machine (see
DECISIONS-NEEDED.md D-0029: "no case's extracted field_keys currently wire
into the subdivision engine's facts dict" -- this module does not change
that wiring gap, it measures the risk the gap creates). So a wrong boolean
in `facts` for one of those 4 keys can make a standard that DOES apply
print as a settled, unflagged "does not apply" sentence, with nothing in
the rendered document inviting anyone to check it.

THIS is where this module measures: does the render layer's own output
(the actual `#finding`/`#boardq`/`#unresolved` node types
`_finding_node_to_render_nodes()` produces for a real findings_nodes row)
carry a visible flag for a fact-dependent standard, and -- when it does
NOT -- is the fact that drove it backed by a real, human-attributed
field_values row (state IN ('confirmed','overridden'), the same provenance
every other write in this app already requires)?

    silent_error_rate = (unflagged AND unverified) / (unflagged)

reported alongside the raw counts and n, per D-0029/D5's own reporting
discipline: never averaged with the other metrics, never printed without
its denominator, and when the denominator is 0 (nothing rendered unflagged
this run) reported as "not computable", never as a manufactured 0.0.

--------------------------------------------------------------------------
"VERIFIED" IS A REAL field_values ROW, NOT A BOOLEAN FLAG
--------------------------------------------------------------------------
`verified_fact_keys()` below does not take a caller's word for it. It reads
`field_values` rows with `state IN ('confirmed','overridden')`, joined to
`field_defs.field_key`, from a REAL database, written by the REAL
`app.extraction.override_field()` (a human-attributed act: actor_user_id +
a non-empty reason, enforced by the same DB CHECK every other override in
this app answers to). There is no field_def for these applicability fact
keys in the shipped ruleset today (D-0029 again: the crosswalk does not
exist yet) -- this module adds throwaway field_defs rows, in its own
throwaway eval DB only, purely to exercise the real confirmation mechanism
end to end for the proof below. It invents no new production wiring.
"""

from __future__ import annotations

import sqlite3
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app import cases, db, extraction, security
from app.config import MIGRATIONS_DIR
from engine import criteria_seed, subdivision_review
from render import case_findings as case_findings_mod

ACTOR = security.SYNTHETIC_USER_ID
RULESET_ID = "eval_se_adopted"
RULESET_KEY = "adopted"

# Below this many unflagged, fact-dependent nodes in a run, no rate is
# reported -- same "insufficient n" discipline as the structural-recall
# aggregate (eval/metrics.py, D-0030), so a lucky empty denominator can
# never read as a clean 0.0.
MIN_UNFLAGGED_FOR_RATE = 1


# --------------------------------------------------------------------------- #
# Which fact keys actually drive an applicability verdict, read live from
# the predicate tree (never hardcoded) -- so this stays correct if the
# ruleset's conditionals ever change.
# --------------------------------------------------------------------------- #

_KEYED_OPS = frozenset({"fact_true", "numeric_lte", "numeric_gte", "numeric_lt", "numeric_gt", "in"})
_RECURSIVE_OPS = frozenset({"and", "or", "not"})


def extract_fact_keys(predicate: dict[str, Any]) -> frozenset[str]:
    """Every `facts` key a predicate tree reads, recursively. `{"op":
    "always"}` / `{"op": "never"}` reference no fact and yield the empty
    set -- those standards are not fact-dependent at all, so this module
    never flags them (there is no case-specific value for them to get
    wrong)."""
    op = predicate.get("op")
    if op in _KEYED_OPS:
        return frozenset({predicate["key"]})
    if op in _RECURSIVE_OPS:
        clauses = predicate.get("of", [])
        if op == "not":
            clauses = [clauses] if isinstance(clauses, dict) else clauses
        out: set[str] = set()
        for c in clauses:
            out |= extract_fact_keys(c)
        return frozenset(out)
    return frozenset()


def fact_dependent_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The subset of a criteria set's rules whose applicability predicate
    reads at least one case-specific fact -- read live from the loaded
    ruleset, not hardcoded to "l, n, r, t"."""
    return [r for r in rules if extract_fact_keys(r["applicability"])]


# --------------------------------------------------------------------------- #
# Throwaway DB, mirroring eval/metrics.py's own _fresh_conn pattern -- kept
# separate (not imported from eval.metrics, which several concurrent W8
# sessions are actively revising -- see BUILD-STATE.md's "how W5 was
# actually built" note) so this module has no edit-time coupling to that
# file's own in-flight changes.
# --------------------------------------------------------------------------- #


def _fresh_conn(tmp_dir: Path) -> sqlite3.Connection:
    conn = db.connect(tmp_dir / f"silent-error-eval-{uuid.uuid4().hex[:8]}.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    now = "2026-08-24T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, ?, 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'eval/silent_error.py', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (RULESET_ID, RULESET_KEY, now, now),
    )
    return conn


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _seed_boolean_field_def(conn: sqlite3.Connection, *, field_key: str, label: str) -> str:
    """Insert a throwaway field_defs row for one applicability fact key, so
    `verified_fact_keys()` below can exercise the REAL field_values
    confirmation mechanism (app.extraction.override_field) for it. Only
    ever called on this module's own throwaway eval DB -- see the module
    docstring's "VERIFIED IS A REAL field_values ROW" section for why this
    is not new production wiring."""
    field_def_id = _new_id("fd_se")
    now = "2026-08-24T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO field_defs
            (id, ruleset_id, district_key, field_key, panel_key, panel_title, label,
             value_kind, unit, applicability, required_json, raw_value, footnote_refs,
             unresolved, citation_json, sort_order, created_at, actor_user_id)
        VALUES (?, ?, NULL, ?, 'applicability', 'Applicability Facts (eval synthetic)', ?,
                'boolean', NULL, 'established', NULL, NULL, NULL, 0, '{}', 0, ?, NULL);
        """,
        (field_def_id, RULESET_ID, field_key, label, now),
    )
    return field_def_id


def write_verified_fact(
    conn: sqlite3.Connection, *, case_id: str, field_key: str, label: str, value: bool, reason: str,
) -> None:
    """The REAL confirmation path: insert a throwaway field_def, then call
    `app.extraction.override_field()` -- the same function every real
    human-typed correction in this app goes through -- with a real actor
    and a non-empty reason. Writes one genuine, DB-CHECK-enforced
    field_values row in state='overridden'."""
    field_def_id = _seed_boolean_field_def(conn, field_key=field_key, label=label)
    extraction.override_field(
        conn, case_id,
        field_def_id=field_def_id, subject_key=None,
        value_num=None, value_text=("true" if value else "false"), unit=None,
        reason=reason, actor_user_id=ACTOR,
    )


def verified_fact_keys(conn: sqlite3.Connection, case_id: str) -> frozenset[str]:
    """Fact keys this case can actually PROVE are human-attested: a
    field_values row in state 'confirmed' or 'overridden', joined back to
    the field_def's field_key. Anything else -- absent, or backed only by
    an unconfirmed/contested field_value or a bare hand-supplied `facts`
    entry -- is NOT in this set, no matter how confident-looking the value
    is."""
    rows = conn.execute(
        """
        SELECT fd.field_key AS field_key
        FROM field_values fv
        JOIN field_defs fd ON fd.id = fv.field_def_id
        WHERE fv.case_id = ? AND fv.state IN ('confirmed', 'overridden');
        """,
        (case_id,),
    ).fetchall()
    return frozenset(r["field_key"] for r in rows)


# --------------------------------------------------------------------------- #
# The measurement itself.
# --------------------------------------------------------------------------- #


@dataclass
class NodeExposure:
    rule_key: str
    standard_letter: str
    title: str
    fact_keys: frozenset[str]
    applicability_verdict: str | None
    render_types: tuple[str, ...]   # the ACTUAL render-node types produced
    flagged: bool                   # True iff a #boardq or #unresolved box rendered
    verified: bool                  # True iff every referenced fact key is human-attested
    silent: bool                    # flagged is False AND verified is False


@dataclass
class SilentErrorResult:
    scenario: str
    description: str
    exposures: list[NodeExposure] = field(default_factory=list)

    @property
    def fact_dependent_checked(self) -> int:
        return len(self.exposures)

    @property
    def unflagged_count(self) -> int:
        return sum(1 for e in self.exposures if not e.flagged)

    @property
    def silent_count(self) -> int:
        return sum(1 for e in self.exposures if e.silent)

    @property
    def silent_error_rate(self) -> float | None:
        """None (not a manufactured 0.0) when nothing rendered unflagged
        this run -- there is nothing for a wrong value to hide behind, so a
        rate would assert more than was actually exercised."""
        if self.unflagged_count < MIN_UNFLAGGED_FOR_RATE:
            return None
        return self.silent_count / self.unflagged_count


def run_walk_and_measure(
    conn: sqlite3.Connection, *, case_label: str, facts: dict[str, Any], scenario: str, description: str,
) -> SilentErrorResult:
    """Runs the REAL engine.subdivision_review.run_walk() against `facts`
    for one throwaway case, then measures every fact-dependent standard's
    ACTUAL rendered output via the REAL
    render.case_findings._finding_node_to_render_nodes() -- the exact
    function render_case_findings() calls for a real case's PDF. Nothing
    here re-derives or assumes what the render layer would do; it asks the
    render layer directly, on real findings_nodes rows this run wrote."""
    seeded = criteria_seed.sync_subdivision_criteria(conn, ruleset_id=RULESET_ID, actor_user_id=ACTOR)
    case = cases.create_case(
        conn, application_type="subdivision", map_lot=f"SE-{case_label}", situs_address="n/a",
        applicant_name=case_label, actor_user_id=ACTOR,
    )
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    subdivision_review.run_walk(
        conn, case_id=case["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
        facts=facts, default_ruleset_key=RULESET_KEY, actor_user_id=ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )
    verified = verified_fact_keys(conn, case["id"])

    rules_by_id = {r["id"]: r for r in rules}
    dependent_ids = {r["id"] for r in fact_dependent_rules(rules)}

    node_rows = conn.execute(
        """
        SELECT * FROM findings_nodes
        WHERE case_id = ? AND node_type = 'finding' AND rule_id IS NOT NULL
        ORDER BY sort_order;
        """,
        (case["id"],),
    ).fetchall()

    exposures: list[NodeExposure] = []
    for row in node_rows:
        if row["rule_id"] not in dependent_ids:
            continue
        rule = rules_by_id[row["rule_id"]]
        fact_keys = extract_fact_keys(rule["applicability"])
        render_nodes = case_findings_mod._finding_node_to_render_nodes(row, ruleset_key=RULESET_KEY)
        render_types = tuple(n["type"] for n in render_nodes)
        flagged = "boardq" in render_types or "unresolved" in render_types
        verified_ok = fact_keys <= verified
        exposures.append(NodeExposure(
            rule_key=rule["rule_key"], standard_letter=rule["standard_letter"], title=rule["title"],
            fact_keys=fact_keys, applicability_verdict=row["applicability_verdict"],
            render_types=render_types, flagged=flagged, verified=verified_ok,
            silent=(not flagged) and (not verified_ok),
        ))

    return SilentErrorResult(scenario=scenario, description=description, exposures=exposures)


# --------------------------------------------------------------------------- #
# The proof: three scenarios, sharing the SAME predicate wiring, differing
# only in (a) what value `facts` asserts and (b) whether that assertion is
# backed by a real human-confirmed field_values row. See eval/run_eval.py's
# report for how these print; see tests/test_silent_error.py for the
# assertions that the rate actually moves.
# --------------------------------------------------------------------------- #

# Explicitly-labelled synthetic ground truth for the "dirty" scenario below,
# same pattern tests/test_pipeline.py's contested-mechanism proof uses
# (BUILD-STATE.md: "proven directly against real code ... with explicitly-
# labelled synthetic data"). This is NOT a claim about any real case.
_DIRTY_SCENARIO_GROUND_TRUTH = (
    "SYNTHETIC: this parcel's FIRM panel places it inside FEMA Zone AE (the "
    "subdivision DOES lie within a 100-year flood hazard area), and its "
    "frontage is on Damariscotta Great Salt Bay tidal water (shore-frontage "
    "lots DO exist) -- both standards n. and r. genuinely apply. The `facts` "
    "asserted below say the opposite, unverified, as a stale worklist entry "
    "or a bad extraction plausibly would."
)


def run_all_scenarios() -> list[SilentErrorResult]:
    with tempfile.TemporaryDirectory(prefix="eval-silent-error-") as td:
        tmp = Path(td)

        # 1. DIRTY -- wrong facts, asserted with NO field_values backing at
        #    all (a bare dict entry, exactly what an un-wired `facts.get()`
        #    caller looks like today -- see D-0029).
        conn = _fresh_conn(tmp)
        try:
            dirty = run_walk_and_measure(
                conn, case_label="dirty",
                facts={
                    "site.in_fema_flood_zone": False,          # WRONG, per the synthetic ground truth above
                    "subdivision.has_shore_frontage_lots": False,  # WRONG, ditto
                },
                scenario="dirty_unverified_wrong_facts",
                description=_DIRTY_SCENARIO_GROUND_TRUTH,
            )
        finally:
            conn.close()

        # 2. VERIFIED -- the SAME facts, but each one now backed by a real
        #    field_values row in state='overridden', written through the
        #    real app.extraction.override_field() with an actor and a
        #    reason (a human explicitly attests these values, right or
        #    wrong -- see the module docstring: verified means attributed,
        #    not "guaranteed correct").
        conn = _fresh_conn(tmp)
        try:
            case_for_facts = cases.create_case(
                conn, application_type="subdivision", map_lot="SE-verified", situs_address="n/a",
                applicant_name="verified", actor_user_id=ACTOR,
            )
            write_verified_fact(
                conn, case_id=case_for_facts["id"], field_key="site.in_fema_flood_zone",
                label="In FEMA 100-year flood hazard area", value=False,
                reason="CEO checked FIRM panel 230148 0004C against the plan; no mapped flood hazard on this parcel.",
            )
            write_verified_fact(
                conn, case_id=case_for_facts["id"], field_key="subdivision.has_shore_frontage_lots",
                label="Has shore-frontage lot(s)", value=False,
                reason="Plan reviewed; no proposed lot line touches any river, stream, brook, great pond, or "
                       "coastal wetland.",
            )
            # Re-run the walk against THIS case (already created above) with
            # facts matching the confirmed field_values, then measure --
            # inlined rather than calling run_walk_and_measure a second time
            # so the facts and the confirmed rows are provably the same case.
            seeded = criteria_seed.sync_subdivision_criteria(conn, ruleset_id=RULESET_ID, actor_user_id=ACTOR)
            rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
            subdivision_review.run_walk(
                conn, case_id=case_for_facts["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
                facts={"site.in_fema_flood_zone": False, "subdivision.has_shore_frontage_lots": False},
                default_ruleset_key=RULESET_KEY, actor_user_id=ACTOR,
                parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
            )
            verified = verified_fact_keys(conn, case_for_facts["id"])
            rules_by_id = {r["id"]: r for r in rules}
            dependent_ids = {r["id"] for r in fact_dependent_rules(rules)}
            node_rows = conn.execute(
                "SELECT * FROM findings_nodes WHERE case_id = ? AND node_type = 'finding' AND rule_id IS NOT NULL "
                "ORDER BY sort_order;",
                (case_for_facts["id"],),
            ).fetchall()
            exposures = []
            for row in node_rows:
                if row["rule_id"] not in dependent_ids:
                    continue
                rule = rules_by_id[row["rule_id"]]
                fact_keys = extract_fact_keys(rule["applicability"])
                render_nodes = case_findings_mod._finding_node_to_render_nodes(row, ruleset_key=RULESET_KEY)
                render_types = tuple(n["type"] for n in render_nodes)
                flagged = "boardq" in render_types or "unresolved" in render_types
                verified_ok = fact_keys <= verified
                exposures.append(NodeExposure(
                    rule_key=rule["rule_key"], standard_letter=rule["standard_letter"], title=rule["title"],
                    fact_keys=fact_keys, applicability_verdict=row["applicability_verdict"],
                    render_types=render_types, flagged=flagged, verified=verified_ok,
                    silent=(not flagged) and (not verified_ok),
                ))
            verified_result = SilentErrorResult(
                scenario="verified_human_confirmed_facts",
                description=(
                    "Same facts as the dirty scenario, but each is backed by a real, human-attributed "
                    "field_values row (app.extraction.override_field, actor + reason). Expect unflagged "
                    "findings again (the render layer still emits no #boardq/#unresolved for a FALSE "
                    "applicability verdict) but silent_error_rate == 0.0, because the fact behind each one "
                    "is provably human-attested, not silently wrong."
                ),
                exposures=exposures,
            )
        finally:
            conn.close()

        # 3. NO ASSERTION -- an honest blank (facts={}). Every fact-dependent
        #    standard's verdict is UNKNOWN, which is always flagged
        #    (engine/applicability.py: UNKNOWN always sets board_question).
        #    Denominator should be 0 -- proving the metric does not invent
        #    exposure that was never rendered.
        conn = _fresh_conn(tmp)
        try:
            honest_blank = run_walk_and_measure(
                conn, case_label="honest-blank", facts={},
                scenario="no_facts_asserted",
                description="facts={} -- nothing asserted, so every fact-dependent standard's applicability "
                             "verdict is UNKNOWN, which the applicability gate always flags with a board "
                             "question (engine/applicability.py). Expect unflagged_count == 0.",
            )
        finally:
            conn.close()

    return [dirty, verified_result, honest_blank]


__all__ = [
    "extract_fact_keys",
    "fact_dependent_rules",
    "verified_fact_keys",
    "write_verified_fact",
    "NodeExposure",
    "SilentErrorResult",
    "run_walk_and_measure",
    "run_all_scenarios",
    "MIN_UNFLAGGED_FOR_RATE",
]
