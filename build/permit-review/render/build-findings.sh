#!/usr/bin/env bash
# Render a Findings of Fact & Conclusions of Law draft markdown file to PDF in
# the Newcastle house style. Near-clone of build/build-memo.sh's proven
# pandoc -> Typst invocation, retargeted at style/findings-template.typ.
#
# Deliberately calls NOTHING else in build/ (extractability: this script plus
# style/findings-template.typ plus style/fonts/ is the whole render path, and
# could be lifted into a standalone tool without the rest of this repo).
#
# Usage:
#   build-findings.sh <in.md> <out.pdf> [meeting-date] [caption] [running-head]
#
# Env vars (booleans; anything other than 1/true/yes/on is treated as off):
#   DRAFT=1        stamp a DRAFT watermark on every page (default: ON — every
#                  document this app produces is a draft until the Board
#                  adopts it at a meeting; see CONTRACT.md's framing rule)
#   PROVENANCE=0   show small gray citation superscripts (default: OFF)
#
# <out.pdf> MUST resolve inside APP/data/exports/ (CONTRACT.md §6.3, §8.6 —
# "the ONLY PDF output directory"); this script refuses to write anywhere else.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"                      # build/permit-review
REPO_ROOT="$(cd "$APP_ROOT/../.." && pwd)"                    # repo root
TEMPLATE="$REPO_ROOT/style/findings-template.typ"
FONTS="$REPO_ROOT/style/fonts"
EXPORTS_DIR="$APP_ROOT/data/exports"

IN="${1:?usage: build-findings.sh <in.md> <out.pdf> [meeting-date] [caption] [running-head]}"
OUT="${2:?output pdf path required}"
MEETING_DATE="${3:-}"
CAPTION="${4:-}"
RUNHEAD="${5:-}"

[ -f "$IN" ] || { echo "findings markdown not found: $IN" >&2; exit 1; }
[ -f "$TEMPLATE" ] || { echo "template not found: $TEMPLATE" >&2; exit 1; }

is_true() {
  case "${1:-}" in
    1 | [Tt][Rr][Uu][Ee] | [Yy][Ee][Ss] | [Oo][Nn]) return 0 ;;
    *) return 1 ;;
  esac
}

# CONTRACT.md §6.3 / §8.6: data/exports/ is the ONLY PDF output directory.
# Resolve OUT's parent (it may not exist yet) and refuse anything outside.
mkdir -p "$(dirname "$OUT")"
OUT_DIR_REAL="$(cd "$(dirname "$OUT")" && pwd)"
mkdir -p "$EXPORTS_DIR"
EXPORTS_DIR_REAL="$(cd "$EXPORTS_DIR" && pwd)"
case "$OUT_DIR_REAL" in
  "$EXPORTS_DIR_REAL" | "$EXPORTS_DIR_REAL"/*) : ;;
  *)
    echo "refusing to write outside data/exports/: $OUT" >&2
    echo "  (expected somewhere under: $EXPORTS_DIR_REAL)" >&2
    exit 1
    ;;
esac

command -v pandoc >/dev/null || { echo "pandoc not found on PATH" >&2; exit 1; }
command -v typst  >/dev/null || { echo "typst not found on PATH"  >&2; exit 1; }

PANDOC_ARGS=(
  "$IN"
  --from=markdown+pipe_tables+fancy_lists+startnum+raw_attribute
  --pdf-engine=typst
  --pdf-engine-opt=--font-path="$FONTS"
  --template="$TEMPLATE"
  -V "meeting-date=$MEETING_DATE"
  -V "caption=$CAPTION"
  -V "running-head=$RUNHEAD"
)

# Only ever pass -V draft=true / -V provenance=true for "on". Pandoc's $if$
# treats ANY non-empty string (including the literal text "false") as truthy,
# so "off" means omitting the flag entirely, never passing =false. (Guarded
# with if/fi rather than `&&` — under `set -e`, a false `&&` chain would exit
# the whole script the moment a toggle is off.)
if is_true "${DRAFT:-1}"; then PANDOC_ARGS+=(-V draft=true); fi
if is_true "${PROVENANCE:-0}"; then PANDOC_ARGS+=(-V provenance=true); fi

PANDOC_ARGS+=(-o "$OUT")

pandoc "${PANDOC_ARGS[@]}"

echo "Findings PDF: $OUT"
