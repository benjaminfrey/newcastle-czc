"""The condition language for form definitions and screener rules.

Conditions are data (dicts from YAML/JSON), never executed. The same cases are
evaluated by portal/web/src/forms/expr.ts and checked against one shared
fixture file, so the browser and the API always agree.

A missing or null value makes a comparison unknown (None), never false:
all/any/not combine true, false and unknown in the usual three-valued way.
An "I don't know yet" answer ({"unknown": true}) reads as missing.
"""

from numbers import Real

_COMPARE = {"gt", "gte", "lt", "lte"}
_BINARY = {"eq", "ne", "has", "oneof"} | _COMPARE
_MISSING = object()


def _get(data, path: str):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return _MISSING
        cur = cur[part]
    return _MISSING if _is_unknown(cur) else cur


def _is_unknown(v) -> bool:
    return isinstance(v, dict) and v == {"unknown": True}


def _is_scalar(v) -> bool:
    return v is None or isinstance(v, (str, bool, Real))


def _is_number(v) -> bool:
    return isinstance(v, Real) and not isinstance(v, bool)


def _same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_number(a) and _is_number(b):
        return a == b
    return type(a) is type(b) and a == b


def validate(expr) -> None:
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError(f"a condition is a mapping with exactly one operator: {expr!r}")
    (op, arg), = expr.items()
    if op in ("all", "any"):
        if not isinstance(arg, list):
            raise ValueError(f"{op} takes a list of conditions")
        for e in arg:
            validate(e)
    elif op == "not":
        validate(arg)
    elif op == "known":
        if not isinstance(arg, str):
            raise ValueError("known takes a path")
    elif op in _BINARY:
        if not (isinstance(arg, list) and len(arg) == 2 and isinstance(arg[0], str)):
            raise ValueError(f"{op} takes [path, value]")
        if op in _COMPARE and not _is_number(arg[1]):
            raise ValueError(f"{op} compares with a number")
        if op == "oneof" and not (isinstance(arg[1], list) and all(_is_scalar(x) for x in arg[1])):
            raise ValueError("oneof takes [path, [values]]")
        if op in ("eq", "ne", "has") and not _is_scalar(arg[1]):
            raise ValueError(f"{op} compares with a single value, not a list or mapping")
    else:
        raise ValueError(f"unknown operator {op!r}")


def evaluate(expr: dict, data: dict) -> bool | None:
    (op, arg), = expr.items()
    if op == "all":
        results = [evaluate(e, data) for e in arg]
        return False if False in results else (None if None in results else True)
    if op == "any":
        results = [evaluate(e, data) for e in arg]
        return True if True in results else (None if None in results else False)
    if op == "not":
        r = evaluate(arg, data)
        return None if r is None else not r
    if op == "known":
        return _get(data, arg) is not _MISSING
    path, value = arg
    v = _get(data, path)
    if v is _MISSING:
        return None
    if op == "eq":
        return _same(v, value)
    if op == "ne":
        return not _same(v, value)
    if op == "has":
        return any(_same(x, value) for x in v) if isinstance(v, list) else None
    if op == "oneof":
        return any(_same(v, x) for x in value)
    if not _is_number(v):
        return None
    return {"gt": v > value, "gte": v >= value, "lt": v < value, "lte": v <= value}[op]


def shown(show_if: dict | None, data: dict) -> bool:
    """A question is asked unless its condition is known to be false: an answer
    still missing, or a property fact nobody knows, keeps the question in."""
    return show_if is None or evaluate(show_if, data) is not False
