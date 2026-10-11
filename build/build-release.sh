#!/usr/bin/env bash
# build-release.sh -- one command for a DRAFT release, and the gate it must pass.
#
#   bash build/build-release.sh <version> [date] --old-ver=<ref>
#        [--plan-only] [--out-dir DIR] [--calls FILE]
#
#   <version>    a decimal draft version (v0.25-draft). A whole number is refused:
#                adoption runs through build-adoption.sh (Wave 4b), never here.
#   [date]       the cover/footer date (default: today, "Month D, YYYY")
#   --old-ver    the git ref the release is compared against (required; must be a commit)
#   --plan-only  print the release plan (JSON) on stdout and stop: no release dir, no staging
#   --out-dir    the release directory itself (default releases/<version>)
#   --calls FILE a person's written calls for NEEDS-CALL Articles (release_plan.py)
#
# Environment: SRC_DIR is the NEW tree (default source/). ADOPTION_MODE must be unset
# or "draft".
#
# Sequence (the first failure stops the run; nothing is placed until the gate passes):
#   1. refusals: --old-ver present and a commit; draft version; draft mode; source dir
#   2. an existing release dir may hold only `Summary of Changes <v>.md` (+ .pdf), and
#      no hidden files (.DS_Store included) --
#      the hand-written Summary is carried into staging byte for byte
#   3. staging dir beside the release dir (.staging-<v>.XXXXXX); an EXIT trap removes it
#      and the temp section-map dir on every path except the successful move
#   4. section_map.py derive (exit 2 = below the similarity floor: no map, said so;
#      exit 1 = refuse) then selfcheck
#   5. release_plan.py -> release-plan.json + ships.json (--plan-only prints and stops)
#   6. build every planned artifact INTO STAGING, names taken from the plan:
#      integrated, integrated redline (pdf+md), each standalone, each standalone
#      redline, the Use Table Changes memo (md+pdf), the Summary skeleton
#   7. release_gate.py plan staging -- refuses a missing, empty, unplanned or
#      mis-paginated file, so a leaf that exits 0 having written nothing is caught
#   8. move into place; pdf_recap (report only); "Release <v>: N file(s) -> <dir>"
#
# Test seams (default: the real scripts; a test seam only, like ADOPTION_MAP):
#   CZC_LEAF_FULL, CZC_LEAF_REDLINE_FULL, CZC_LEAF_STANDALONE, CZC_LEAF_REDLINE_STANDALONE
#   each a script run as `bash "$CZC_LEAF_X" <the real script's arguments>`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$REPO_ROOT/build"

LEAF_FULL="${CZC_LEAF_FULL:-$BUILD/build-full-czc.sh}"
LEAF_REDLINE_FULL="${CZC_LEAF_REDLINE_FULL:-$BUILD/build-redline-full.sh}"
LEAF_STANDALONE="${CZC_LEAF_STANDALONE:-$BUILD/build-standalone.sh}"
LEAF_REDLINE_STANDALONE="${CZC_LEAF_REDLINE_STANDALONE:-$BUILD/build-redline-standalone.sh}"

unset SECTION_MAP   # only ever set by this driver, from a map it derived
refuse() { echo "build-release: $*" >&2; exit 1; }
say() { echo "build-release: $*" >&2; }

VERSION="" DATE_STR="" OLD_VER="" PLAN_ONLY=0 OUT_DIR_ARG="" CALLS=""
POS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --old-ver=*) OLD_VER="${1#--old-ver=}" ;;
    --old-ver) [ $# -ge 2 ] || refuse "--old-ver needs a value"; OLD_VER="$2"; shift ;;
    --plan-only) PLAN_ONLY=1 ;;
    --out-dir=*) OUT_DIR_ARG="${1#--out-dir=}" ;;
    --out-dir) [ $# -ge 2 ] || refuse "--out-dir needs a value"; OUT_DIR_ARG="$2"; shift ;;
    --calls=*) CALLS="${1#--calls=}" ;;
    --calls) [ $# -ge 2 ] || refuse "--calls needs a value"; CALLS="$2"; shift ;;
    -*) refuse "unknown option '$1'" ;;
    *)
      POS=$((POS + 1))
      case "$POS" in
        1) VERSION="$1" ;;
        2) DATE_STR="$1" ;;
        *) refuse "unexpected argument '$1'" ;;
      esac ;;
  esac
  shift
done

# --- 1. refusals, before anything is created --------------------------------
[ -n "$VERSION" ] || refuse "usage: build-release.sh <version> [date] --old-ver=<ref> [--plan-only] [--out-dir DIR] [--calls FILE]"
[ -n "$OLD_VER" ] || refuse "--old-ver=<ref> is required: a release is a comparison against the previous version."
git -C "$REPO_ROOT" rev-parse --verify --quiet "${OLD_VER}^{commit}" >/dev/null \
  || refuse "--old-ver '$OLD_VER' is not a git commit."
VS_MSG="$(python3 "$BUILD/version_state.py" --require draft "$VERSION" 2>&1)" \
  || refuse "'$VERSION' cannot be released here (draft versions only; adoption runs through build-adoption.sh). $VS_MSG"
case "${ADOPTION_MODE:-draft}" in
  draft) ;;
  *) refuse "ADOPTION_MODE=${ADOPTION_MODE} is set; a draft release runs in draft mode only." ;;
esac
NEW_DIR="${SRC_DIR:-$REPO_ROOT/source}"
[ -d "$NEW_DIR" ] || refuse "source directory '$NEW_DIR' does not exist."
NEW_DIR="$(cd "$NEW_DIR" && pwd)"
if [ -n "$CALLS" ]; then
  [ -f "$CALLS" ] || refuse "calls file '$CALLS' does not exist."
  CALLS="$(cd "$(dirname "$CALLS")" && pwd)/$(basename "$CALLS")"
fi
[ -n "$DATE_STR" ] || DATE_STR="$(date +"%B %-d, %Y")"

RELEASE_DIR="${OUT_DIR_ARG:-$REPO_ROOT/releases/$VERSION}"
SUMMARY_MD_NAME="Summary of Changes $VERSION.md"
SUMMARY_PDF_NAME="Summary of Changes $VERSION.pdf"
KEEP_SUMMARY=0
if [ -e "$RELEASE_DIR" ]; then
  [ -d "$RELEASE_DIR" ] || refuse "'$RELEASE_DIR' exists and is not a directory."
  OTHER=0 HAVE_PDF=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      "$SUMMARY_MD_NAME") KEEP_SUMMARY=1 ;;
      "$SUMMARY_PDF_NAME") HAVE_PDF=1 ;;
      *) OTHER=1 ;;
    esac
  done < <(find "$RELEASE_DIR" -mindepth 1 -maxdepth 1 -exec basename {} \;)
  if [ "$HAVE_PDF" = 1 ] && [ "$KEEP_SUMMARY" = 0 ]; then
    refuse "release directory '$RELEASE_DIR' holds '$SUMMARY_PDF_NAME' without its .md; refusing to touch it."
  fi
  if [ "$OTHER" = 1 ]; then
    refuse "release directory '$RELEASE_DIR' already holds files other than the Summary of Changes; refusing to touch it."
  fi
fi

# --- 3. staging + trap --------------------------------------------------------
STAGING="" MAPDIR="" PLANTMP=""
cleanup() {
  [ -z "$STAGING" ] || rm -rf "$STAGING"
  [ -z "$MAPDIR" ] || rm -rf "$MAPDIR"
  [ -z "$PLANTMP" ] || rm -rf "$PLANTMP"
}
trap cleanup EXIT

MAPDIR="$(mktemp -d "${TMPDIR:-/tmp}/czc-secmap.XXXXXX")"
if [ "$PLAN_ONLY" = 1 ]; then
  PLANTMP="$(mktemp -d "${TMPDIR:-/tmp}/czc-plan.XXXXXX")"
  WORK="$PLANTMP"
else
  mkdir -p "$(dirname "$RELEASE_DIR")"
  STAGING="$(mktemp -d "$(cd "$(dirname "$RELEASE_DIR")" && pwd)/.staging-$VERSION.XXXXXX")"
  WORK="$STAGING"
fi

# --- 4. section map -------------------------------------------------------------
MAP_FILE="$MAPDIR/section-map.json"
set +e
python3 "$BUILD/section_map.py" derive "$OLD_VER" --new-dir "$NEW_DIR" --out "$MAP_FILE" >&2
RC=$?
set -e
MAP_ARGS=()
case "$RC" in
  0)
    python3 "$BUILD/section_map.py" selfcheck "$MAP_FILE" --old-ref "$OLD_VER" --new-dir "$NEW_DIR" >&2 \
      || refuse "the derived section map failed its selfcheck."
    MAP_ARGS=(--section-map "$MAP_FILE")
    export SECTION_MAP="$MAP_FILE" ;;
  2) say "section map: below the similarity floor; proceeding with no map." ;;
  *) refuse "section_map.py derive refused (exit $RC)." ;;
esac

# --- 5. plan ----------------------------------------------------------------------
PLAN="$WORK/release-plan.json"
SHIPS="$WORK/ships.json"
CALLS_ARGS=()
[ -z "$CALLS" ] || CALLS_ARGS=(--calls "$CALLS")
python3 "$BUILD/release_plan.py" --old "$OLD_VER" --new-dir "$NEW_DIR" --version "$VERSION" \
  --date "$DATE_STR" --out "$PLAN" --ships "$SHIPS" ${MAP_ARGS[@]+"${MAP_ARGS[@]}"} \
  ${CALLS_ARGS[@]+"${CALLS_ARGS[@]}"} >&2 \
  || refuse "release_plan.py refused; no release was built."

if [ "$PLAN_ONLY" = 1 ]; then
  cat "$PLAN"
  exit 0
fi

# plan_files KIND -> "<article>|<file>" per line (article empty when null)
plan_files() {
  python3 - "$PLAN" "$1" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1], encoding="utf-8"))
for a in plan["artifacts"]:
    if a["kind"] == sys.argv[2]:
        for f in a["files"]:
            print(f'{"" if a.get("article") is None else a["article"]}|{f}')
PY
}

PLIST="$MAPDIR/plan-list"
plan_list() { plan_files "$1" > "$PLIST" || refuse "could not read the release plan ($1)"; }

export SRC_DIR="$NEW_DIR"

# --- 6. build into staging ----------------------------------------------------------
say "building the integrated Code"
OUT_DIR="$STAGING" bash "$LEAF_FULL" "$VERSION" "$DATE_STR" >&2 \
    || refuse "the integrated build failed (exit $?)"

RL_PDF="" RL_MD=""
plan_list integrated-redline
while IFS='|' read -r _ f; do
  [ -n "$f" ] || continue
  case "$f" in *.pdf) RL_PDF="$f" ;; *.md) RL_MD="$f" ;; esac
done < "$PLIST"
if [ -n "$RL_PDF" ]; then
  say "building the integrated redline"
  REDLINE_OUT="$STAGING/$RL_PDF" REDLINE_MD_OUT="${RL_MD:+$STAGING/$RL_MD}" \
    bash "$LEAF_REDLINE_FULL" "$VERSION" "$OLD_VER" "$DATE_STR" >&2 \
    || refuse "the integrated redline build failed (exit $?)"
fi

plan_list standalone
while IFS='|' read -r art f; do
  [ -n "$art" ] || continue
  case "$f" in *.pdf) ;; *) continue ;; esac   # one call per Article builds pdf+md
  NN=$(printf "%02d" "$((10#$art))")
  say "building the Article $art standalone"
  OUT_DIR="$STAGING" bash "$LEAF_STANDALONE" "$NN" "$VERSION" "$DATE_STR" >&2 \
    || refuse "the Article $art standalone build failed (exit $?)"
done < "$PLIST"

plan_list standalone-redline
while IFS='|' read -r art f; do
  [ -n "$art" ] || continue
  case "$f" in *.pdf) ;; *) continue ;; esac
  NN=$(printf "%02d" "$((10#$art))")
  say "building the Article $art standalone redline"
  REDLINE_OUT="$STAGING" bash "$LEAF_REDLINE_STANDALONE" "$NN" "$VERSION" "$OLD_VER" "$DATE_STR" >&2 \
    || refuse "the Article $art standalone redline build failed (exit $?)"
done < "$PLIST"

UT_MD="" UT_PDF=""
plan_list use-table-changes
while IFS='|' read -r _ f; do
  [ -n "$f" ] || continue
  case "$f" in *.pdf) UT_PDF="$f" ;; *.md) UT_MD="$f" ;; esac
done < "$PLIST"
if [ -n "$UT_MD" ]; then
  say "building the Use Table Changes memo"
  set +e
  python3 "$BUILD/use_table_changes.py" "$OLD_VER" "$STAGING/$UT_MD" --new-dir "$NEW_DIR" >&2
  RC=$?
  set -e
  [ "$RC" = 0 ] || refuse "use_table_changes.py exited $RC but the plan lists a Use Table Changes memo."
  if [ -n "$UT_PDF" ]; then
    bash "$BUILD/build-memo.sh" "$STAGING/$UT_MD" "$STAGING/$UT_PDF" \
      "Use Table Changes — $VERSION" "Newcastle Core Zoning Code · $DATE_STR" >&2 \
    || refuse "the Use Table Changes memo build failed (exit $?)"
  fi
fi

if [ "$KEEP_SUMMARY" = 1 ]; then
  say "keeping the existing hand-written Summary of Changes"
  cp -p "$RELEASE_DIR/$SUMMARY_MD_NAME" "$STAGING/$SUMMARY_MD_NAME"
  [ ! -f "$RELEASE_DIR/$SUMMARY_PDF_NAME" ] || cp -p "$RELEASE_DIR/$SUMMARY_PDF_NAME" "$STAGING/$SUMMARY_PDF_NAME"
else
  python3 "$BUILD/summary_skeleton.py" "$PLAN" "$STAGING/$SUMMARY_MD_NAME" >&2 \
    || refuse "summary_skeleton.py refused."
fi

# --- 7. gate ---------------------------------------------------------------------------
python3 "$BUILD/release_gate.py" "$PLAN" "$STAGING" >&2 \
  || refuse "the release gate refused; nothing was released."

# --- 8. place ---------------------------------------------------------------------------
# mktemp/mkstemp made staging 0700 and its files 0600; a release is read by others.
chmod 755 "$STAGING" || refuse "could not set permissions on staging."
find "$STAGING" -mindepth 1 -maxdepth 1 -type f -exec chmod 644 {} + \
  || refuse "could not set permissions on staged files."
if [ -d "$RELEASE_DIR" ]; then
  # Existing (Summary-only or empty) release dir: move in everything but the Summary
  # files already there, so their bytes are never rewritten. The gate guarantees
  # staging holds only planned files.
  find "$STAGING" -mindepth 1 -maxdepth 1 -exec basename {} \; > "$MAPDIR/placing" \
    || refuse "could not list the staged files."
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ "$KEEP_SUMMARY" = 1 ]; then
      case "$f" in "$SUMMARY_MD_NAME"|"$SUMMARY_PDF_NAME") continue ;; esac
    fi
    mv "$STAGING/$f" "$RELEASE_DIR/$f" || refuse "could not place '$f' in '$RELEASE_DIR'."
  done < "$MAPDIR/placing"
  chmod 755 "$RELEASE_DIR" || refuse "could not set permissions on '$RELEASE_DIR'."
else
  mv "$STAGING" "$RELEASE_DIR" || refuse "could not move the release into '$RELEASE_DIR'."
  STAGING=""
fi

COUNT=$(find "$RELEASE_DIR" -mindepth 1 -maxdepth 1 ! -name '.*' | wc -l | tr -d ' ')
RECAP=()
while IFS= read -r p; do
  [ -n "$p" ] || continue
  RECAP+=("$(basename "$p")=$p")
done < <(find "$RELEASE_DIR" -mindepth 1 -maxdepth 1 -name '*.pdf' | sort)
[ "${#RECAP[@]}" -eq 0 ] || python3 "$BUILD/pdf_recap.py" "${RECAP[@]}" >&2 || true
echo "Release $VERSION: $COUNT file(s) -> $RELEASE_DIR"
