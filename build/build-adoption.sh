#!/usr/bin/env bash
# Freeze a draft into a TOWN MEETING EDITION. See build/ADOPTION-SPEC.md §3.3.
#
# Freezes THROUGH the release driver (build-release.sh, ADOPTION_MODE=meeting), into
# releases/<version>/: the Town Meeting edition and its redline vs the PREVIOUSLY
# ADOPTED Code, an extract and redline for every Article that changed in substance,
# the Use Table Changes memo whenever district tables moved, and a Summary of
# Changes skeleton -- then writes frozen-from.json. This script keeps its own
# gates (version state, baseline self-check, breakdown, dirty-source refusal).
#
# It does NOT stamp an adoption date. The vote has not happened.
#
# Test seams (tests only): CZC_LEAF_RELEASE (a script run in place of build-release.sh)
# and ADOPTION_MAP (an alternative adoption map). Any other build override in the
# environment (SRC_DIR, OUT_DIR, ...) is REFUSED: the freeze records the tree of
# source/, so the driver must build from exactly that tree.
#
# Usage:  build-adoption.sh <version> <meeting-date> [--dry-run] [--freeze-date=<date>]
#                           [--calls FILE]
#         build-adoption.sh <version> <meeting-date> --render-summary
#           renders "Summary of Changes <version>.pdf" from the hand-written .md in
#           the frozen packet, and does nothing else.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
MEETING_DATE="${2:-}"
DRY_RUN=0
RENDER_SUMMARY=0
CALLS=""
CALLS_GIVEN=0
FREEZE_DATE_GIVEN=0
# The date the packet is FROZEN -- today, not the meeting date. These are two
# different facts and the cover states both: line 2 says "for adoption at Town
# Meeting, <meeting-date>", line 3 says "Frozen <freeze-date>". Passing the
# meeting date for both (the bug found in the final review) printed "Frozen
# March 15, 2027" on a document frozen months earlier -- a provenance line
# stating a future date. Overridable so a rebuild of an already-frozen packet
# reproduces the original cover rather than stamping today over it.
FREEZE_DATE="$(date +"%B %-d, %Y")"

# Any argument beyond the two required positionals must be a recognised flag.
# The entire safety story of this command is "preview before you build" -- a
# mistyped flag (--dryrun, -n, --dry-run given past position 3) must REFUSE,
# not silently fall through to the branch that leaves a shipped-looking
# releases/<version>/ directory behind.
if [ $# -gt 2 ]; then
  NEXT_IS_CALLS=0
  for ARG in "${@:3}"; do
    if [ "$NEXT_IS_CALLS" = "1" ]; then
      CALLS="$ARG"
      CALLS_GIVEN=1
      NEXT_IS_CALLS=0
      continue
    fi
    case "$ARG" in
      --dry-run)
        DRY_RUN=1
        ;;
      --render-summary)
        RENDER_SUMMARY=1
        ;;
      --calls=*)
        CALLS="${ARG#--calls=}"
        CALLS_GIVEN=1
        ;;
      --calls)
        NEXT_IS_CALLS=1
        ;;
      --freeze-date=*)
        FREEZE_DATE="${ARG#--freeze-date=}"
        FREEZE_DATE_GIVEN=1
        if [ -z "$FREEZE_DATE" ]; then
          echo "build-adoption.sh: --freeze-date= requires a date." >&2
          exit 1
        fi
        ;;
      *)
        echo "build-adoption.sh: unrecognised argument '$ARG' -- refusing rather " \
             "than silently building a release. The recognised flags are " \
             "--dry-run, --freeze-date=<date>, --calls FILE and --render-summary." >&2
        exit 1
        ;;
    esac
  done
  if [ "$NEXT_IS_CALLS" = "1" ]; then
    echo "build-adoption.sh: --calls requires a file." >&2
    exit 1
  fi
fi

if [ "$RENDER_SUMMARY" = "1" ] && { [ "$DRY_RUN" = "1" ] || [ "$CALLS_GIVEN" = "1" ] || [ "$FREEZE_DATE_GIVEN" = "1" ]; }; then
  echo "build-adoption.sh: --render-summary renders the Summary and nothing else; it cannot be combined with --dry-run, --calls or --freeze-date." >&2
  exit 1
fi

if [ -z "$VERSION" ] || [ -z "$MEETING_DATE" ]; then
  echo "usage: build-adoption.sh <version> <meeting-date> [--dry-run] [--freeze-date=<date>] [--calls FILE] [--render-summary]" >&2
  exit 1
fi
if [ "$CALLS_GIVEN" = "1" ] && [ -z "$CALLS" ]; then
  echo "build-adoption.sh: --calls requires a file." >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

# --- --render-summary: render the hand-written Summary and do nothing else. ---
# No rebuild, no re-freeze, no other file touched (so no --freeze-date needed).
if [ "$RENDER_SUMMARY" = "1" ]; then
  PACKET="$REPO_ROOT/releases/$VERSION"
  SUMMARY="$PACKET/Summary of Changes $VERSION.md"
  SUMMARY_PDF="$PACKET/Summary of Changes $VERSION.pdf"
  if [ ! -d "$PACKET" ]; then
    echo "build-adoption.sh: --render-summary: no frozen packet at $PACKET; freeze first." >&2
    exit 1
  fi
  if [ ! -f "$SUMMARY" ]; then
    echo "build-adoption.sh: --render-summary: $SUMMARY does not exist." >&2
    exit 1
  fi
  if python3 - "$REPO_ROOT/build" "$SUMMARY" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
import summary_skeleton
text = open(sys.argv[2], encoding="utf-8").read()
sys.exit(0 if summary_skeleton.PLACEHOLDER in text else 1)
PYEOF
  then
    echo "build-adoption.sh: --render-summary: the Summary is still the generated skeleton" >&2
    echo "(its placeholder comment is present). Write it by hand first; refusing." >&2
    exit 1
  fi
  bash "$REPO_ROOT/build/build-memo.sh" "$SUMMARY" "$SUMMARY_PDF" \
    "Summary of Changes — $VERSION" \
    "Newcastle Core Zoning Code · Town Meeting, $MEETING_DATE"
  echo "Rendered Summary PDF: $SUMMARY_PDF"
  exit 0
fi

BASELINE="$(python3 -c "
import sys; sys.path.insert(0,'$REPO_ROOT/build')
import adoption_map; print(adoption_map.load().baseline_version)")"

echo "Freezing $VERSION for Town Meeting, $MEETING_DATE (frozen $FREEZE_DATE)"
echo "Previously adopted version: $BASELINE"
echo

# --- Has the map been rolled over since the last adoption? -------------------
# Once an adoption version becomes the baseline, adoption-map.json must be
# reset to identity (spec §3.1). Nothing performs that edit, and getting it
# half right fails SILENTLY: a stale article_numbers rewrites the old side's
# "Article 4" to "Article 5" and reports hundreds of changes nobody made.
# The invariant is that the baseline compared against ITSELF marks zero lines.
# Dormant while the baseline is v0.1-baseline; arms itself at the rollover.
python3 "$REPO_ROOT/build/baseline_selfcheck.py" || exit 1
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

# --- The freeze must be tied to a COMMIT, not just to a moment. --------------
# build-adopted.sh renders the adopted edition from the `<version>` TAG, never
# from the working tree, and that is the whole of the "cannot contain anything
# the voters did not see" property. But nothing used to connect the two: the
# meeting edition is rendered from the WORKING TREE, so if the tree was
# dirty, or if the tag was later moved forward (which this repo does habitually
# on re-cuts -- see the czc-release skill's release flow), the identity gate would compare
# two equally-new artifacts and pass vacuously.
#
# Two halves close it:
#   (a) refuse to freeze from a dirty source/ tree, so HEAD:source really IS
#       what was rendered;
#   (b) record the source TREE object HEAD:source resolves to, and have
#       build-adopted.sh require the tag to still resolve to the same tree.
# The tree object, not the commit sha, is the right thing to pin: the release
# directory produced below is itself committed and tagged afterwards, so the
# tag's commit is legitimately NOT the commit that was HEAD at freeze time --
# but its source/ tree must be byte-identical or the voters saw something else.
for V in SRC_DIR OUT_DIR OUT_NAME_OVERRIDE STANDALONE_FRONT_NOTE SECTION_MAP REDLINE_OUT \
         REDLINE_MD_OUT CZC_LEAF_FULL CZC_LEAF_REDLINE_FULL CZC_LEAF_STANDALONE \
         CZC_LEAF_REDLINE_STANDALONE FRONT_NOTE_PDF OUT_MD_SOURCE REDLINE_CAVEAT; do
  if [ -n "${!V:-}" ]; then
    echo "Refusing to freeze: $V is set in the environment." >&2
    echo "The freeze records the tree of source/ and the driver would build from" >&2
    echo "'$V' instead, so the packet could differ from what is recorded. Unset it." >&2
    exit 1
  fi
done
DIRTY="$(git -C "$REPO_ROOT" status --porcelain -- source)"
if [ -n "$DIRTY" ]; then
  echo "Refusing to freeze: source/ has uncommitted or untracked changes." >&2
  echo "$DIRTY" >&2
  echo >&2
  echo "The Town Meeting edition is rendered from the working tree, but the" >&2
  echo "ADOPTED edition is rendered from the '$VERSION' tag. Those must be the" >&2
  echo "same content, and that can only be asserted if what is rendered now is" >&2
  echo "committed. Commit (or stash) source/ and re-run." >&2
  exit 1
fi
FROZEN_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
FROZEN_SOURCE_TREE="$(git -C "$REPO_ROOT" rev-parse "HEAD:source")"

OUT="$REPO_ROOT/releases/$VERSION"

# The packet is built by the release driver in Town Meeting mode: the Town
# Meeting edition, its redline vs the previously adopted Code, an extract and
# a redline for every Article that changed in substance, the Use Table Changes
# memo whenever district tables moved, and a Summary skeleton. The driver
# gates everything before placing anything, and refuses an existing release
# directory; if it refuses, nothing here is written either.
# CZC_LEAF_RELEASE is a TEST SEAM ONLY (a script run in place of build-release.sh).
LEAF_RELEASE="${CZC_LEAF_RELEASE:-$REPO_ROOT/build/build-release.sh}"
DRIVER_ARGS=("$VERSION" "$FREEZE_DATE" "--old-ver=$BASELINE")
if [ -n "$CALLS" ]; then
  DRIVER_ARGS+=("--calls" "$CALLS")
fi
OUT_PRE_EXISTED=0
[ -e "$OUT" ] && OUT_PRE_EXISTED=1
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$LEAF_RELEASE" "${DRIVER_ARGS[@]}" || {
    if [ -d "$OUT" ] && [ "$OUT_PRE_EXISTED" = "0" ]; then
      echo "build-adoption.sh: the freeze FAILED after the driver placed $OUT; it is incomplete" >&2
      echo "(no frozen-from.json). Remove it and re-run." >&2
    else
      echo "build-adoption.sh: the release driver refused or failed; nothing was frozen." >&2
    fi
    exit 1
  }
[ -d "$OUT" ] || { echo "build-adoption.sh: the driver succeeded but $OUT does not exist." >&2; exit 1; }

# The freeze provenance record, read and enforced by build-adopted.sh.
PROVENANCE="$OUT/frozen-from.json"
if ! python3 - "$PROVENANCE" "$VERSION" "$MEETING_DATE" "$FREEZE_DATE" \
         "$FROZEN_COMMIT" "$FROZEN_SOURCE_TREE" <<'PYEOF'
import json, sys
out, version, meeting, frozen, commit, tree = sys.argv[1:7]
json.dump({
    "_README": (
        "Written by build-adoption.sh at freeze time; verified by "
        "build-adopted.sh before the adopted edition is rendered. "
        "frozen_source_tree is the git tree object of source/ that the Town "
        "Meeting edition was rendered from. The adopted edition is rendered "
        "from the '<version>' tag, so that tag's source/ tree must still equal "
        "this value -- otherwise the tag was moved after the freeze and the "
        "adopted document could contain text the voters never saw."
    ),
    "version": version,
    "meeting_date": meeting,
    "frozen_on": frozen,
    "frozen_from_commit": commit,
    "frozen_source_tree": tree,
}, open(out, "w"), indent=2)
open(out, "a").write("\n")
print(f"Wrote freeze provenance: {out}")
PYEOF
then
  echo "build-adoption.sh: writing frozen-from.json FAILED; $OUT is incomplete. Remove it and re-run." >&2
  exit 1
fi

echo
echo "Town Meeting edition $VERSION built into releases/$VERSION/"
echo "Frozen from commit $FROZEN_COMMIT (source tree $FROZEN_SOURCE_TREE)"
echo
echo "NEXT:"
echo "  1. Write the Summary by hand in releases/$VERSION/ (replace the generated skeleton),"
echo "     then render it: build-adoption.sh $VERSION \"$MEETING_DATE\" --render-summary"
echo "  (To re-freeze, first remove releases/$VERSION/ -- the driver refuses an existing packet.)"
echo "  2. Commit releases/$VERSION/ and tag $VERSION at that commit."
echo "     The tag's source/ tree must stay $FROZEN_SOURCE_TREE -- build-adopted.sh"
echo "     refuses if the tag is later moved onto different source."
