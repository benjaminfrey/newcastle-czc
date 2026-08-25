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
# Usage:  build-adoption.sh <version> <meeting-date> [--dry-run] [--freeze-date=<date>]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/build/adoption-name.sh"
VERSION="${1:-}"
MEETING_DATE="${2:-}"
DRY_RUN=0
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
  for ARG in "${@:3}"; do
    case "$ARG" in
      --dry-run)
        DRY_RUN=1
        ;;
      --freeze-date=*)
        FREEZE_DATE="${ARG#--freeze-date=}"
        if [ -z "$FREEZE_DATE" ]; then
          echo "build-adoption.sh: --freeze-date= requires a date." >&2
          exit 1
        fi
        ;;
      *)
        echo "build-adoption.sh: unrecognised argument '$ARG' -- refusing rather " \
             "than silently building a release. The recognised flags are " \
             "--dry-run and --freeze-date=<date>." >&2
        exit 1
        ;;
    esac
  done
fi

if [ -z "$VERSION" ] || [ -z "$MEETING_DATE" ]; then
  echo "usage: build-adoption.sh <version> <meeting-date> [--dry-run] [--freeze-date=<date>]" >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

BASELINE="$(python3 -c "
import sys; sys.path.insert(0,'$REPO_ROOT/build')
import adoption_map; print(adoption_map.load().baseline_version)")"

echo "Freezing $VERSION for Town Meeting, $MEETING_DATE (frozen $FREEZE_DATE)"
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

# --- The freeze must be tied to a COMMIT, not just to a moment. --------------
# build-adopted.sh renders the adopted edition from the `<version>` TAG, never
# from the working tree, and that is the whole of the "cannot contain anything
# the voters did not see" property. But nothing used to connect the two: this
# script renders the meeting edition from the WORKING TREE, so if the tree was
# dirty, or if the tag was later moved forward (which this repo does habitually
# on re-cuts -- see CLAUDE.md's release flow), the identity gate would compare
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
mkdir -p "$OUT"

MEETING_NAME="$(czc_integrated_name meeting "$VERSION")"

# 1. Town Meeting edition. The cover's two dates are DIFFERENT facts:
#    DATE_STR (positional 2) is when this was frozen; ADOPTION_EVENT_DATE is
#    when the vote happens. See FREEZE_DATE above.
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$FREEZE_DATE"
MEETING_PDF="$OUT/$MEETING_NAME.pdf"

# 2. Redline vs the previously adopted Code. ADOPTION_BASELINE=1 also switches
#    the cover caveat and inserts the §4.3 structural-changes page.
ADOPTION_BASELINE=1 ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-redline-full.sh" "$VERSION" "$BASELINE" "$FREEZE_DATE"
REDLINE_PDF="$OUT/$MEETING_NAME — Redline.pdf"

# 3. Standalone Article 3
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-standalone.sh" 3 "$VERSION" "$FREEZE_DATE"
STANDALONE_PDF="$OUT/Article 3 Thoroughfares (Standalone $VERSION).pdf"

# 3b. The freeze provenance record, read and enforced by build-adopted.sh.
PROVENANCE="$OUT/frozen-from.json"
python3 - "$PROVENANCE" "$VERSION" "$MEETING_DATE" "$FREEZE_DATE" \
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

# 4. Summary skeleton — written by hand, in plain language, no file/path refs.
#
#    NOTHING SUBSTANTIVE IS PRE-ASSERTED HERE. The skeleton used to ship the
#    sentence "No standard, dimension or requirement was made stricter anywhere
#    in this release except as described above" already written. That is a legal
#    claim about the whole Code, asserted by a build script that has not read
#    the Code, in a document a voter relies on — and it is exactly what this
#    project's own honest-blanks rule forbids (an honest blank beats a
#    confident guess; a long confident draft on an unreviewed body of changes
#    is a failure, not a convenience). It is now a blank the author must fill,
#    and the author must fill it against the printed per-article breakdown
#    above.
SUMMARY="$OUT/Summary of Changes $VERSION.md"
SUMMARY_PDF="$OUT/Summary of Changes $VERSION.pdf"
SUMMARY_IS_SKELETON=0
if [ ! -f "$SUMMARY" ]; then
  SUMMARY_IS_SKELETON=1
  cat > "$SUMMARY" <<EOF
# Summary of Changes — $VERSION

**For adoption at Town Meeting, $MEETING_DATE.** Changes are stated against the
Core Zoning Code adopted November 3, 2020 and amended through March 24, 2025.

<!-- Write this by hand, in plain language: by section, by road name, by Type.
     No file, path or script references. -->

<!-- THE REDLINE CANNOT SHOW FOUR THINGS. Each must be described here, in
     prose, or a reader of the packet will never learn it. The redline's own
     structural-changes page states them; this document is where they are
     actually explained:
       1. Article 2 District Standards is reproduced UNMARKED — its standards
          are generated spreads, not prose. Say what changed in Article 2.
       2. Article renumbering (old 3-8 become 4-9) and the table renumbering
          that follows it are suppressed as mechanical. Say so once.
       3. Figures, tables, maps, the Inventory (Exhibit 3.1) and the Type Map
          (Exhibit 3.2) render at current state and carry no marks. Describe
          those changes by Type and by road name.
       4. Article 3 Thoroughfares is entirely new, so its whole text is marked
          as added; the redline cannot tell a reader what matters within it. -->

## What is new

## What changed

## What did not change

<!-- ANSWER THIS DELIBERATELY, do not delete it. Was any standard, dimension or
     requirement made STRICTER than the adopted Code? Read the per-article
     breakdown this build printed before answering, and state the answer
     plainly here — including "yes, in the following places". An unanswered
     question is honest; a pre-written "no" is not. -->
EOF
  echo "Wrote Summary skeleton: $SUMMARY"
fi

# The house release flow renders the Summary to PDF (build-memo.sh + the CZC
# memo template); the adoption path did not, so the one hand-written document
# in the warrant packet was the only one shipping as bare markdown. It is
# rendered only when the Summary was NOT just created — a PDF of an empty
# skeleton is a shipped-looking placeholder, which is worse than none. Re-run
# this command (or build-memo.sh directly) once the Summary is written.
if [ "$SUMMARY_IS_SKELETON" = "0" ]; then
  bash "$REPO_ROOT/build/build-memo.sh" "$SUMMARY" "$SUMMARY_PDF" \
    "Summary of Changes — $VERSION" \
    "Newcastle Core Zoning Code · Town Meeting, $MEETING_DATE"
  echo "Rendered Summary PDF: $SUMMARY_PDF"
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
echo "Frozen from commit $FROZEN_COMMIT (source tree $FROZEN_SOURCE_TREE)"
echo
echo "NEXT:"
echo "  1. Write the Summary by hand, then re-run this command to render its PDF."
echo "  2. Commit releases/$VERSION/ and tag $VERSION at that commit."
echo "     The tag's source/ tree must stay $FROZEN_SOURCE_TREE — build-adopted.sh"
echo "     refuses if the tag is later moved onto different source."
