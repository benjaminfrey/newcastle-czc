#!/usr/bin/env python3
"""Entry point for the Newcastle Permit Review app.

    python3 run.py                     # start the server, print the URL
    python3 run.py --port 8900         # start on a different port (still 127.0.0.1 only)
    python3 run.py --selftest          # offline self-test, no network/server (CONTRACT.md §1 S6)
    python3 run.py --verify-citations  # W2 gate: ruleset_build/verify_citations.py
    python3 run.py --verify-structure  # W2 gate hardening: ruleset_build/verify_structure.py
                                        # (mechanical structural assertions -- also runs as
                                        # part of --selftest, see app/main.py:selftest())
    python3 run.py --eval              # W8 eval harness: eval/run_eval.py -- structural
                                        # recall + coverage, over-conclusion rate, fact fidelity
                                        # + silent_error_rate, all offline; prints "not measured
                                        # (no API key)" (never a fake number) for anything that
                                        # needs a model, incl. prose usefulness

Equivalent to `python -m app.main --selftest` for the self-test form CONTRACT.md
names explicitly; this file is the convenience entry point for everything else.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Newcastle Permit Review")
    parser.add_argument("--port", type=int, default=None,
                         help="override the bound port (default 8781; host is always 127.0.0.1)")
    parser.add_argument("--selftest", action="store_true",
                         help="run the offline self-test and exit (no network, no server)")
    parser.add_argument("--verify-citations", action="store_true",
                         help="run the citation-verification harness (ruleset_build/verify_citations.py) "
                              "and exit; extracts every local CZC citation from the nine real "
                              "Findings of Fact & Conclusions of Law decisions and checks each against "
                              "the adopted ruleset")
    parser.add_argument("--verify-structure", action="store_true",
                         help="run the structural-verification harness (ruleset_build/verify_structure.py) "
                              "and exit; mechanical set-equality/count/sequence assertions over BOTH "
                              "rulesets' Article/Section/Standard node indexes -- the W2 gate hardening "
                              "that replaces a prose 'discrepancy note' with an unskippable assertion")
    parser.add_argument("--eval", action="store_true",
                         help="run the W8 eval harness (eval/run_eval.py) and exit")
    parser.add_argument("--out", type=Path, default=None,
                         help="--verify-citations / --eval only: report path "
                              "(default: data/citation-report.json / stdout only for --eval)")
    parser.add_argument("--quiet", action="store_true",
                         help="--verify-citations / --verify-structure / --eval only: "
                              "print only the final summary line(s)")
    parser.add_argument("--demonstrate-holdout-read", action="store_true",
                         help="--eval only: prove live that the eval harness can read Dalton/Stantec "
                              "(llm/fewshot.py refuses the same read -- see eval/pairs.py)")
    args = parser.parse_args()

    if args.verify_citations:
        from ruleset_build import verify_citations
        return verify_citations.run(out_path=args.out, quiet=args.quiet)

    if args.verify_structure:
        from ruleset_build import verify_structure
        return verify_structure.run(quiet=args.quiet)

    if args.eval:
        from eval import run_eval
        return run_eval.run(
            out_path=args.out, quiet=args.quiet,
            demonstrate_holdout_read=args.demonstrate_holdout_read,
        )

    from app import main as app_main

    if args.selftest:
        return app_main.selftest()

    try:
        import uvicorn
    except ImportError:
        print("uvicorn is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    # CONTRACT.md §1 S3 / app/config.py: HOST is a fixed module constant,
    # never configurable. PORT defaults to 8781 and is overridable ONLY by
    # this --port flag -- never an env var, never a config key -- so it is
    # passed straight into create_app() as a plain argument, not threaded
    # through the environment.
    port = args.port if args.port is not None else app_main.PORT
    app = app_main.create_app(port=port)
    url = f"http://{app_main.HOST}:{port}/"
    print(f"Newcastle Permit Review — starting on {url}")
    print(f"  health check: {url}healthz")
    print("  Ctrl-C to stop.")
    uvicorn.run(app, host=app_main.HOST, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
