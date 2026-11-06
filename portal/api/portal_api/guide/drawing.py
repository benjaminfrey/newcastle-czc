"""What each lot line is, for the drawing (guided plan 4). The applicant chooses the front; the
rest follows the Code's §2 lot rules: a line along a road is never a rear (it is another
frontage), and the rear is the line roughly opposite the front. The drawing shows these; it never
decides anything with them (decision 12).

Which road is the front (the chair, 2026-11-05): a line along an Alley (S5) is never a frontage
(Article 9: "buildings do not front on an Alley"; Article 2: no road frontage may be a rear,
"except an alley"). A corner lot fronts on the road of the highest Type (Article 2: Streets before
Roads, then the lower code), the rule the Code writes for new lots, which the chair applies to
existing ones; its other road is a secondary frontage. Two roads of one Type, roads on opposite
sides (a through lot: the Code defines a secondary frontage only on corner lots) and a road of
unknown Type are the Town's call."""

import math

REAR_WITHIN_DEG = 60
ALLEY = "S5"


def _normal(line: dict) -> tuple[float, float]:
    """Outward unit normal of a line on a clockwise ring (y north): left of the direction of travel."""
    (x0, y0), (x1, y1) = line["points"][0], line["points"][-1]
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1.0
    return (-dy / n, dx / n)


def _off_opposite(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Degrees between b and the direction opposite a."""
    dot = max(-1.0, min(1.0, -(a[0] * b[0] + a[1] * b[1])))
    return math.degrees(math.acos(dot))


def fronting(line: dict) -> bool:
    """A line a lot can front on: along a road, but not an Alley."""
    return bool(line.get("street")) and line["street"].get("type") != ALLEY


def _rank(type_: str | None) -> tuple[int, int] | None:
    """Article 3's hierarchy: Streets (S) before Roads (R), then the lower code."""
    if not type_ or type_[0] not in "SR" or not type_[1:].isdigit():
        return None
    return (0 if type_[0] == "S" else 1, int(type_[1:]))


def frontages(lines: list[dict]) -> dict:
    """The lot's front as the Code finds it: kind "none", "one", "corner" (with its primary and
    secondary frontages) or "town" (the Town decides)."""
    f = [L for L in lines if fronting(L)]
    if len(f) <= 1:
        return {"kind": "one" if f else "none", "primary": f[0]["id"] if f else None, "secondary": []}
    town = {"kind": "town", "primary": None, "secondary": []}
    if not all(L.get("points") for L in f):
        return town
    normals = [_normal(L) for L in f]
    if any(_off_opposite(a, b) <= REAR_WITHIN_DEG for i, a in enumerate(normals) for b in normals[i + 1:]):
        return town
    ranks = [_rank(L["street"].get("type")) for L in f]
    if None in ranks:
        return town
    best = min(ranks)
    if ranks.count(best) > 1:
        return town
    primary = f[ranks.index(best)]["id"]
    return {"kind": "corner", "primary": primary, "secondary": [L["id"] for L in f if L["id"] != primary]}


def roles(lines: list[dict], front_id: str | None) -> dict[str, str] | None:
    front = next((L for L in lines if L["id"] == front_id), None)
    if front is None:
        return None
    fr = frontages(lines)
    other = "secondary" if fr["kind"] == "corner" and fr["primary"] == front_id else "frontage"
    out = {L["id"]: (other if fronting(L) else "side") for L in lines}
    out[front["id"]] = "front"
    n = _normal(front)
    candidates = [(_off_opposite(n, _normal(L)), L["id"]) for L in lines if out[L["id"]] == "side"]
    best = min(candidates, default=None)
    if best is not None and best[0] <= REAR_WITHIN_DEG:
        out[best[1]] = "rear"
    return out
