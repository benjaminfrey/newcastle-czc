"""Implements CONTRACT.md §4.1.1 (district_key / panel_key / use_key /
category_key derivation) for the ruleset_build/ offline builders.
"""

from __future__ import annotations

import re
import unicodedata

# Fixed by table (CONTRACT.md §4.1.1) — NEVER derived from `code`, because
# `code == "SD"` for seven different districts in source/article-02-data.json.
DISTRICT_KEYS: list[str] = [
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "d6",
    "sd-historic",
    "sd-conserve",
    "sd-hwy",
    "sd-rhwy",
    "sd-campus",
    "sd-marine",
    "sd-fab",
]

# (index, code, name) that source/article-02-data.json's district array MUST
# match, in order, before DISTRICT_KEYS may be assigned positionally.
DISTRICT_TABLE: list[tuple[int, str, str]] = [
    (0, "D1", "RURAL"),
    (1, "D2", "NEIGHBORHOOD RESIDENTIAL"),
    (2, "D3", "NEIGHBORHOOD BUSINESS"),
    (3, "D4", "VILLAGE RESIDENTIAL"),
    (4, "D5", "VILLAGE BUSINESS"),
    (5, "D6", "TOWN CENTER"),
    (6, "SD", "HISTORIC"),
    (7, "SD", "CONSERVATION"),
    (8, "SD", "HIGHWAY COMMERCIAL"),
    (9, "SD", "RURAL HIGHWAY"),
    (10, "SD", "CAMPUS"),
    (11, "SD", "MARINE"),
    (12, "SD", "FABRICATION"),
]

assert len(DISTRICT_KEYS) == len(DISTRICT_TABLE) == 13


def slug(s: str) -> str:
    """casefold -> NFKD -> strip soft hyphens -> non-alnum runs to '_' -> strip.

    Used for panel_key / field_key leaves / use_key / category_key.
    NEVER used for district_key — that is fixed by DISTRICT_TABLE (§4.1.1),
    because `code` is not unique.
    """
    s = s.casefold()
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\xad", "")  # strip soft hyphens (U+00AD) explicitly
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def assert_district_table(districts: list[dict]) -> None:
    """Hard-fail if source/article-02-data.json's district array doesn't match
    DISTRICT_TABLE exactly in length, order, code and name. A mismatch here
    means DISTRICT_KEYS can no longer be assigned by position — never guess;
    fail the build instead (CONTRACT.md §4.1.1).
    """
    if len(districts) != len(DISTRICT_TABLE):
        raise AssertionError(
            f"expected {len(DISTRICT_TABLE)} districts in source/article-02-data.json, "
            f"found {len(districts)}"
        )
    for (idx, code, name), d in zip(DISTRICT_TABLE, districts):
        if d.get("code") != code or d.get("name") != name:
            raise AssertionError(
                f"district table mismatch at index {idx}: expected "
                f"(code={code!r}, name={name!r}), got "
                f"(code={d.get('code')!r}, name={d.get('name')!r}) — "
                f"CONTRACT.md §4.1.1 DISTRICT_TABLE is stale or the source moved."
            )


def display_name(name: str) -> str:
    """'RURAL' -> 'Rural', 'NEIGHBORHOOD RESIDENTIAL' -> 'Neighborhood Residential'."""
    return name.title()
