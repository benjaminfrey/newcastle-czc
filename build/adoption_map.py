#!/usr/bin/env python3
"""Reads build/adoption-map.json -- the baseline->current article correspondence.

WHY THIS EXISTS. build-redline-full.sh resolves the OLD side of each article
diff by looking up the same filename at the old tag. That works between two
drafts. It does NOT work against the adopted baseline: 8 of 9 article files were
renamed when Article 3 was inserted, so 8 old-sides come back empty and the
whole Code renders as newly written -- in the document that goes to Town Meeting.
Measured 2026-08-24: exactly one file (article-01-general.md) resolved.

An UNMAPPED file raises. It must never fall through to "new", because that is
precisely the silent failure this module exists to prevent.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "adoption-map.json"


@dataclass(frozen=True)
class AdoptionMap:
    baseline_version: str
    article_numbers: dict[int, int]
    files: dict[str, str | None]

    def baseline_path_for(self, current_basename: str) -> str | None:
        """Baseline filename for a current article file, or None if it is new.

        Raises KeyError for a file the map does not know -- a new or renamed
        article must be added here deliberately, not discovered at render time.
        """
        if current_basename not in self.files:
            raise KeyError(
                f"{current_basename!r} is not in adoption-map.json. Add it "
                f"(with its baseline counterpart, or null if new at this "
                f"adoption) rather than letting it render as wholly new."
            )
        return self.files[current_basename]

    def renumber(self, text: str) -> str:
        """Rewrite 'Article N' cross-references from baseline to current numbering."""
        return re.sub(
            r"\bArticle (\d+)\b",
            lambda m: f"Article {self.article_numbers.get(int(m.group(1)), int(m.group(1)))}",
            text,
        )


def load(path: str | Path | None = None) -> AdoptionMap:
    doc = json.loads(Path(path or DEFAULT_PATH).read_text())
    return AdoptionMap(
        baseline_version=doc["baseline_version"],
        article_numbers={int(k): int(v) for k, v in doc["article_numbers"].items()},
        files=dict(doc["files"]),
    )
