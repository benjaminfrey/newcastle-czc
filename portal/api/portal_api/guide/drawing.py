"""What each lot line is, for the drawing (guided plan 4). The applicant chooses the front; the
rest follows the Code's §2 lot rules: a line along a road is never a rear (it is another
frontage, whose setback is the Town's call), and the rear is the line roughly opposite the front.
The drawing shows these; it never decides anything with them (decision 12)."""

import math

REAR_WITHIN_DEG = 60


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


def roles(lines: list[dict], front_id: str | None) -> dict[str, str] | None:
    front = next((L for L in lines if L["id"] == front_id), None)
    if front is None:
        return None
    out = {L["id"]: ("frontage" if L["street"] else "side") for L in lines}
    out[front["id"]] = "front"
    n = _normal(front)
    candidates = [(_off_opposite(n, _normal(L)), L["id"]) for L in lines if out[L["id"]] == "side"]
    best = min(candidates, default=None)
    if best is not None and best[0] <= REAR_WITHIN_DEG:
        out[best[1]] = "rear"
    return out
