#!/usr/bin/env bash
# Freeze a draft into a TOWN MEETING EDITION. See build/ADOPTION-SPEC.md §3.3.
#
# Produces, into releases/<version>/:
#   1. the Town Meeting edition (integrated PDF + md)
#   2. the redline vs the PREVIOUSLY ADOPTED Code (mapped + normalised)
#   3. the standalone Article 3
#   4. a Summary of Changes skeleton, to be written by hand in plain language
#
# It does NOT stamp an adoption date. The vote has not happened.
#
# Usage:  build-adoption.sh <version> <meeting-date> [--dry-run]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
MEETING_DATE="${2:-}"
DRY_RUN=0

# Any argument beyond the two required positionals must be a recognised flag.
# The entire safety story of this command is "preview before you build" -- a
# mistyped flag (--dryrun, -n, --dry-run given past position 3) must REFUSE,
# not silently fall through to the branch that leaves a shipped-looking
# releases/<version>/ directory behind.
if [ $# -gt 2 ]; then
  for ARG in "${@:3}"; do
    case "$ARG" in
      --dry-run)
        DRY_RUN=1
        ;;
      *)
        echo "build-adoption.sh: unrecognised argument '$ARG' -- refusing rather " \
             "than silently building a release. The only recognised flag is " \
             "--dry-run." >&2
        exit 1
        ;;
    esac
  done
fi

if [ -z "$VERSION" ] || [ -z "$MEETING_DATE" ]; then
  echo "usage: build-adoption.sh <version> <meeting-date> [--dry-run]" >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

BASELINE="$(python3 -c "
import sys; sys.path.insert(0,'$REPO_ROOT/build')
import adoption_map; print(adoption_map.load().baseline_version)")"

echo "Freezing $VERSION for Town Meeting, $MEETING_DATE"
echo "Previously adopted version: $BASELINE"
echo

# --- The substantive-change breakdown, printed BEFORE anything is built. -----
# These are the changes the voters will adopt. They accumulated across 24 drafts
# and have never been reviewed as a set. This is also the instrument the
# packet's headline number is read from, so build/adoption_breakdown.py fails
# LOUDLY (exit 1, "fix the map") on a mapped file it cannot resolve on either
# side, rather than silently mis-totalling -- see that module's docstring.
echo "Substantive changes vs $BASELINE (formatting and renumbering suppressed):"
python3 "$REPO_ROOT/build/adoption_breakdown.py"
echo

if [ "$DRY_RUN" = "1" ]; then
  echo "(dry run — nothing built)"
  exit 0
fi

OUT="$REPO_ROOT/releases/$VERSION"
mkdir -p "$OUT"

# 1. Town Meeting edition
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$MEETING_DATE"
MEETING_PDF="$OUT/Newcastle CZC (Integrated Draft $VERSION).pdf"

# 2. Redline vs the previously adopted Code
ADOPTION_BASELINE=1 ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-redline-full.sh" "$VERSION" "$BASELINE" "$MEETING_DATE"
REDLINE_PDF="$OUT/Newcastle CZC (Integrated Draft $VERSION) — Redline.pdf"

# 3. Standalone Article 3
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-standalone.sh" 3 "$VERSION" "$MEETING_DATE"
STANDALONE_PDF="$OUT/Article 3 Thoroughfares (Standalone $VERSION).pdf"

# 4. Summary skeleton — written by hand, in plain language, no file/path refs.
SUMMARY="$OUT/Summary of Changes $VERSION.md"
if [ ! -f "$SUMMARY" ]; then
  cat > "$SUMMARY" <<EOF
# Summary of Changes — $VERSION

**For adoption at Town Meeting, $MEETING_DATE.** Changes are stated against the
Core Zoning Code adopted November 3, 2020 and amended through March 24, 2025.

<!-- Write this by hand, in plain language: by section, by road name, by Type.
     No file, path or script references. Describe the figure and table changes
     in prose — a redline marks wording only, so the Inventory and the Type Map
     changes will not appear as marked text. -->

## What is new

## What changed

## What did not change

No standard, dimension or requirement was made stricter anywhere in this
release except as described above.
EOF
  echo "Wrote Summary skeleton: $SUMMARY"
fi

# --- Layout recap (ADOPTION-SPEC.md §6.5: page + blank counts per artifact). -
echo
echo "Page / blank counts:"
python3 "$REPO_ROOT/build/pdf_recap.py" \
  "Meeting edition=$MEETING_PDF" \
  "Baseline redline=$REDLINE_PDF" \
  "Standalone Article 3=$STANDALONE_PDF"

echo
echo "Town Meeting edition $VERSION built into releases/$VERSION/"
echo "NEXT: write the Summary by hand, then tag $VERSION when the packet is final."
