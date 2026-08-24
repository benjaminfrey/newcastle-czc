#!/usr/bin/env python3
"""build_fewshot.py -- builds and reports the llm/fewshot.py few-shot index.

    python3 build_fewshot.py                  # build + print a summary
    python3 build_fewshot.py --out PATH        # also write the index as JSON
    python3 build_fewshot.py --quiet           # print only the final summary line
    python3 build_fewshot.py --demonstrate-holdout   # prove the Dalton/Stantec refusal live

Offline: this reads only the local `docs/Findings of Fact and Conclusions
of Law/` fixtures and the local ruleset — no network, no LLM, no key.

W5 task brief: "build_fewshot.py MUST REFUSE to read [holdout pairs]." This
script never calls llm.fewshot.read_application_text()/read_decision_text()
on a holdout pair in its normal build path -- llm.fewshot.build_index()
already excludes them structurally (see that module's docstring). The
--demonstrate-holdout flag exists purely to show the refusal firing live,
for a human running this script to see with their own eyes; the actual
proof that the refusal is enforced IN CODE lives in
tests/test_fewshot.py's test that calls the same function this flag calls,
with pymupdf.open() monkeypatched to assert it is never reached.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from llm import fewshot  # noqa: E402

DEFAULT_OUT = APP_ROOT / "data" / "fewshot-index.json"


def _index_as_json(index: dict[tuple[str, str], tuple]) -> dict:
    out: dict[str, list[dict]] = {}
    for (review_type, rule_id), examples in sorted(index.items()):
        key = f"{review_type}::{rule_id}"
        out[key] = [
            {
                "pair_name": ex.pair_name,
                "review_type": ex.review_type,
                "rule_id": ex.rule_id,
                "source_document": ex.source_document,
                "page": ex.page,
                "citation_raw": ex.citation_raw,
                "decision_excerpt": ex.decision_excerpt,
            }
            for ex in examples
        ]
    return out


def _write_json_atomic(payload: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    tmp = out_path.with_name(out_path.name + f".tmp-{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()


def print_summary(index: dict[tuple[str, str], tuple]) -> None:
    total_examples = sum(len(v) for v in index.values())
    pairs_seen = sorted({ex.pair_name for exs in index.values() for ex in exs})
    review_types = sorted({rt for (rt, _rid) in index})

    print(f"llm/fewshot.py index: {len(index)} (review_type, rule_id) buckets, "
          f"{total_examples} examples, from {len(pairs_seen)} matched pairs")
    print(f"  matched pairs used : {', '.join(pairs_seen)}")
    print(f"  holdout (unread)   : {', '.join(sorted(fewshot.HOLDOUT_NAMES))}")
    print(f"  review types       : {', '.join(review_types)}")
    print()
    print("  top buckets by example count:")
    for (review_type, rule_id), examples in sorted(
        index.items(), key=lambda kv: -len(kv[1])
    )[:10]:
        print(f"    {review_type:<20} {rule_id:<16} {len(examples)} example(s)")


def demonstrate_holdout() -> int:
    """Actually attempt the refused reads, live, and print what happened.
    Exits non-zero if either holdout pair is somehow readable (which would
    mean the enforcement in llm/fewshot.py is broken)."""
    failures = 0
    for name in sorted(fewshot.HOLDOUT_NAMES):
        pair = fewshot.get_pair(name)
        try:
            fewshot.read_application_text(pair)
        except fewshot.HoldoutError as exc:
            print(f"  {name}: REFUSED as expected -- {exc}")
        else:
            print(f"  {name}: !! NOT refused -- enforcement is broken !!")
            failures += 1
    return 1 if failures else 0


def run(*, out_path: Path | None, quiet: bool, demonstrate: bool) -> int:
    if demonstrate:
        print("Demonstrating holdout enforcement (attempting to read Dalton, Stantec):")
        rc = demonstrate_holdout()
        if rc != 0:
            return rc
        print()

    index = fewshot.build_index()

    if out_path is not None:
        _write_json_atomic(_index_as_json(index), out_path)

    if quiet:
        total_examples = sum(len(v) for v in index.values())
        print(
            f"FEWSHOT: {len(index)} buckets, {total_examples} examples, "
            f"{fewshot.MATCHED_PAIR_COUNT} matched pairs, "
            f"{fewshot.HOLDOUT_COUNT} held out"
        )
    else:
        print_summary(index)
        if out_path is not None:
            display = out_path.relative_to(APP_ROOT) if APP_ROOT in out_path.resolve().parents else out_path
            print()
            print(f"Index written to {display}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build + report llm/fewshot.py's index")
    parser.add_argument("--out", type=Path, default=None, help="also write the index as JSON here")
    parser.add_argument("--quiet", action="store_true", help="print only the final FEWSHOT: summary line")
    parser.add_argument(
        "--demonstrate-holdout",
        action="store_true",
        dest="demonstrate",
        help="attempt (and show refused) reads of the Dalton/Stantec holdout pairs before building",
    )
    args = parser.parse_args(argv)
    return run(out_path=args.out, quiet=args.quiet, demonstrate=args.demonstrate)


if __name__ == "__main__":
    raise SystemExit(main())
