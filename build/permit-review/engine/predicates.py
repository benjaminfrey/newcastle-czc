"""The applicability gate's predicate language. W6 task brief: "THE
APPLICABILITY GATE. Deterministic only. THREE-VALUED: TRUE / FALSE /
UNKNOWN. No `eval`, no arbitrary code -- a tiny predicate language.
UNKNOWN NEVER SUPPRESSES A NODE."

A predicate is plain JSON-able data -- a dict with an "op" key -- built at
ruleset-build time (ruleset_build/build_subdivision_criteria.py) and stored
verbatim in rules.applicability_json. evaluate() interprets that data
against a case's known facts. There is no eval(), no exec(), no getattr()
dispatch on caller-supplied strings, and no way for data to name a Python
callable: the only functions ever invoked are the fixed handlers wired into
_OPS below, chosen by exact string match against a closed set of names.
Passing an unrecognised "op" is a hard error (PredicateError), never a
silent False/UNKNOWN.

Verdict uses the same three string values findings_nodes.applicability_verdict
(app/migrations/0013_findings_tree.sql) stores -- 'true' | 'false' | 'unknown'
-- so a Verdict can be written to that column with zero translation, and a
row read back from it can be turned straight into a Verdict.

Facts come from a plain `dict[str, Any]` the caller assembles from whatever
is actually known about the case (today: nothing wires this to real ingest
data yet -- that is a later workflow's job). A KEY ABSENT from facts, or
present with value None, means "we do not know" -- it evaluates to UNKNOWN,
never to False. This is CONTRACT.md §1 S7's "no silent guessing" applied to
applicability specifically: a missing fact must never quietly read as "does
not apply".
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PredicateError(ValueError):
    """Malformed predicate data: an unknown "op", a missing required key, or
    a value of the wrong shape. Raised at evaluation time so a bad predicate
    in a build artifact fails loudly rather than silently mis-evaluating.
    """


class Verdict(str, Enum):
    """Three-valued applicability outcome. Subclasses str so a Verdict
    compares equal to, and can be stored/loaded as, the plain strings
    findings_nodes.applicability_verdict's CHECK constraint expects.
    """

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    def __bool__(self) -> bool:  # pragma: no cover - defensive
        # Deliberately NOT implemented as a truthy/falsy shortcut. Kleene
        # logic below never relies on Python truthiness of a Verdict; this
        # override exists only so an accidental `if verdict:` fails loudly
        # (TypeError) instead of silently treating UNKNOWN as truthy/falsy.
        raise TypeError(
            "Verdict has no truth value -- compare explicitly against "
            "Verdict.TRUE / Verdict.FALSE / Verdict.UNKNOWN (this guards "
            "against 'UNKNOWN' silently behaving as True or False)"
        )


# --------------------------------------------------------------------------- #
# Kleene (strong) three-valued logic for NOT / AND / OR.
#
#   NOT unknown = unknown
#   x AND unknown = unknown   unless x is FALSE, in which case FALSE AND
#                              anything is FALSE (a known-false clause
#                              already decides an AND regardless of the rest)
#   x OR  unknown = unknown   unless x is TRUE,  in which case TRUE OR
#                              anything is TRUE
# --------------------------------------------------------------------------- #


def _not(v: Verdict) -> Verdict:
    if v is Verdict.TRUE:
        return Verdict.FALSE
    if v is Verdict.FALSE:
        return Verdict.TRUE
    return Verdict.UNKNOWN


def _and_pair(a: Verdict, b: Verdict) -> Verdict:
    if a is Verdict.FALSE or b is Verdict.FALSE:
        return Verdict.FALSE
    if a is Verdict.TRUE and b is Verdict.TRUE:
        return Verdict.TRUE
    return Verdict.UNKNOWN


def _or_pair(a: Verdict, b: Verdict) -> Verdict:
    if a is Verdict.TRUE or b is Verdict.TRUE:
        return Verdict.TRUE
    if a is Verdict.FALSE and b is Verdict.FALSE:
        return Verdict.FALSE
    return Verdict.UNKNOWN


def _kleene_and(verdicts: list[Verdict]) -> Verdict:
    result = Verdict.TRUE
    for v in verdicts:
        result = _and_pair(result, v)
    return result


def _kleene_or(verdicts: list[Verdict]) -> Verdict:
    result = Verdict.FALSE
    for v in verdicts:
        result = _or_pair(result, v)
    return result


# --------------------------------------------------------------------------- #
# Fact lookup helpers. A fact that is absent, or explicitly None, is
# "unknown" -- the one rule every op below shares.
# --------------------------------------------------------------------------- #

_MISSING = object()


def _lookup(facts: dict[str, Any], key: str) -> Any:
    val = facts.get(key, _MISSING)
    if val is _MISSING or val is None:
        return _MISSING
    return val


# --------------------------------------------------------------------------- #
# Op handlers. Each takes (node: dict, facts: dict, evaluate: Callable) and
# returns a Verdict. `evaluate` is passed in (rather than the handlers
# calling the module-level evaluate() by name) purely so this file has one
# obvious recursion point for "and"/"or"/"not" to call back through -- it is
# still always THIS module's evaluate(), never a caller-suppliable function.
# --------------------------------------------------------------------------- #


def _op_always(node: dict, facts: dict, evaluate) -> Verdict:
    return Verdict.TRUE


def _op_never(node: dict, facts: dict, evaluate) -> Verdict:
    return Verdict.FALSE


def _require_key(node: dict, key: str) -> str:
    if key not in node:
        raise PredicateError(f"predicate op {node.get('op')!r} requires a {key!r} key: {node!r}")
    return node[key]


def _op_fact_true(node: dict, facts: dict, evaluate) -> Verdict:
    """TRUE if facts[key] is True, FALSE if facts[key] is False, UNKNOWN if
    the key is absent/None, or PredicateError if present but not a bool."""
    key = _require_key(node, "key")
    val = _lookup(facts, key)
    if val is _MISSING:
        return Verdict.UNKNOWN
    if not isinstance(val, bool):
        raise PredicateError(
            f"fact_true: facts[{key!r}] must be a bool, got {type(val).__name__}: {val!r}"
        )
    return Verdict.TRUE if val else Verdict.FALSE


def _op_not(node: dict, facts: dict, evaluate) -> Verdict:
    inner = _require_key(node, "of")
    return _not(evaluate(inner, facts))


def _op_and(node: dict, facts: dict, evaluate) -> Verdict:
    clauses = _require_key(node, "of")
    if not isinstance(clauses, list) or not clauses:
        raise PredicateError(f"and: 'of' must be a non-empty list: {node!r}")
    return _kleene_and([evaluate(c, facts) for c in clauses])


def _op_or(node: dict, facts: dict, evaluate) -> Verdict:
    clauses = _require_key(node, "of")
    if not isinstance(clauses, list) or not clauses:
        raise PredicateError(f"or: 'of' must be a non-empty list: {node!r}")
    return _kleene_or([evaluate(c, facts) for c in clauses])


def _numeric_fact(node: dict, facts: dict) -> Any:
    key = _require_key(node, "key")
    val = _lookup(facts, key)
    if val is _MISSING:
        return _MISSING
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise PredicateError(
            f"predicate op {node.get('op')!r}: facts[{key!r}] must be numeric, "
            f"got {type(val).__name__}: {val!r}"
        )
    return val


def _op_numeric_lte(node: dict, facts: dict, evaluate) -> Verdict:
    val = _numeric_fact(node, facts)
    if val is _MISSING:
        return Verdict.UNKNOWN
    threshold = _require_key(node, "value")
    return Verdict.TRUE if val <= threshold else Verdict.FALSE


def _op_numeric_gte(node: dict, facts: dict, evaluate) -> Verdict:
    val = _numeric_fact(node, facts)
    if val is _MISSING:
        return Verdict.UNKNOWN
    threshold = _require_key(node, "value")
    return Verdict.TRUE if val >= threshold else Verdict.FALSE


def _op_numeric_lt(node: dict, facts: dict, evaluate) -> Verdict:
    val = _numeric_fact(node, facts)
    if val is _MISSING:
        return Verdict.UNKNOWN
    threshold = _require_key(node, "value")
    return Verdict.TRUE if val < threshold else Verdict.FALSE


def _op_numeric_gt(node: dict, facts: dict, evaluate) -> Verdict:
    val = _numeric_fact(node, facts)
    if val is _MISSING:
        return Verdict.UNKNOWN
    threshold = _require_key(node, "value")
    return Verdict.TRUE if val > threshold else Verdict.FALSE


def _op_in(node: dict, facts: dict, evaluate) -> Verdict:
    key = _require_key(node, "key")
    values = _require_key(node, "values")
    if not isinstance(values, list):
        raise PredicateError(f"in: 'values' must be a list: {node!r}")
    val = _lookup(facts, key)
    if val is _MISSING:
        return Verdict.UNKNOWN
    return Verdict.TRUE if val in values else Verdict.FALSE


# Fixed dispatch table -- the ONLY names evaluate() will ever act on. Adding
# a new op means adding a new entry here in code review, not something data
# can do on its own.
_OPS = {
    "always": _op_always,
    "never": _op_never,
    "fact_true": _op_fact_true,
    "not": _op_not,
    "and": _op_and,
    "or": _op_or,
    "numeric_lte": _op_numeric_lte,
    "numeric_gte": _op_numeric_gte,
    "numeric_lt": _op_numeric_lt,
    "numeric_gt": _op_numeric_gt,
    "in": _op_in,
}


def evaluate(node: dict, facts: dict[str, Any]) -> Verdict:
    """Evaluate one predicate node against `facts`. Recurses for and/or/not.
    Raises PredicateError for malformed data; never returns anything other
    than a Verdict member; never calls eval/exec/getattr on data.
    """
    if not isinstance(node, dict):
        raise PredicateError(f"predicate node must be a dict, got {type(node).__name__}: {node!r}")
    op = node.get("op")
    handler = _OPS.get(op)
    if handler is None:
        raise PredicateError(f"unknown predicate op {op!r} (known ops: {sorted(_OPS)})")
    return handler(node, facts, evaluate)


# The "no gate" predicate every rule defaults to (rules.applicability_json's
# column default in 0014_criteria_kind.sql is the JSON-serialized form of
# this same literal, {"op": "always"}).
ALWAYS: dict = {"op": "always"}
