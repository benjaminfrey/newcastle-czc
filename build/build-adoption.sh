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
[ "${3:-}" = "--dry-run" ] && DRY_RUN=1

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
# and have never been reviewed as a set.
#
# An article flagged not-text-comparable in adoption-map.json (its content
# moved OUT of markdown into a native-Typst unit since the baseline -- Article
# 2's district standards, into article-02.typ) is skipped here exactly as
# redline_resolve.py skips it when rendering: diffing it would report a move
# as a mass deletion (thousands of phantom lines), which is precisely what
# that flag exists to prevent. See adoption_map.py's module docstring.
echo "Substantive changes vs $BASELINE (formatting and renumbering suppressed):"
python3 - <<PYEOF
import sys, subprocess, difflib
sys.path.insert(0, "$REPO_ROOT/build")
import adoption_map, normalize_for_diff as nz
m = adoption_map.load()
total = 0
for cur, base in sorted(m.files.items()):
    if base is None:
        print(f"  {cur:40s}   NEW at this adoption")
        continue
    reason = m.not_text_comparable_reason(cur)
    if reason is not None:
        print(f"  {cur:40s}   NOT TEXT-COMPARABLE (rendered unmarked): {reason}")
        continue
    o = subprocess.run(["git", "-C", "$REPO_ROOT", "show", f"{m.baseline_version}:source/{base}"],
                       capture_output=True, text=True).stdout
    try:
        n = open(f"$REPO_ROOT/source/{cur}").read()
    except FileNotFoundError:
        continue
    on = nz.normalize(o, amap=m, is_baseline_side=True).splitlines()
    nn = nz.normalize(n, amap=m, is_baseline_side=False).splitlines()
    c = sum(1 for l in difflib.unified_diff(on, nn, n=0)
            if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    total += c
    print(f"  {cur:40s} {c:5d} lines")
print(f"  {'TOTAL':40s} {total:5d} substantive changed lines")
PYEOF
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

# 2. Redline vs the previously adopted Code
ADOPTION_BASELINE=1 ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-redline-full.sh" "$VERSION" "$BASELINE" "$MEETING_DATE"

# 3. Standalone Article 3
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-standalone.sh" 3 "$VERSION" "$MEETING_DATE"

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

echo
echo "Town Meeting edition $VERSION built into releases/$VERSION/"
echo "NEXT: write the Summary by hand, then tag $VERSION when the packet is final."
