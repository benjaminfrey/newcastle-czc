#!/usr/bin/env bash
# Render a memo markdown file to a polished PDF in the Newcastle CZC house style.
#
# Usage:
#   build-memo.sh <memo.md> <out.pdf> [running-head] [foot-note]
#
# Uses style/memo-template.typ (CZC typography: Barlow, article-blue headings,
# hairline tables). The source markdown is left untouched; a temp copy is
# lightly preprocessed (letterhead line breaks + drop the warning emoji).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$REPO_ROOT/style/memo-template.typ"
FONTS="$REPO_ROOT/style/fonts"

IN="${1:?usage: build-memo.sh <memo.md> <out.pdf> [running-head] [foot-note]}"
OUT="${2:?output pdf path required}"
RUNHEAD="${3:-}"
FOOT="${4:-}"

[ -f "$IN" ] || { echo "memo not found: $IN" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"

TMP="$(mktemp -t memo).md"
trap 'rm -f "$TMP"' EXIT

# Preprocess on the temp copy only:
#   - hard-break the To/From/Date/Re letterhead lines (append two trailing spaces)
#   - drop the ⚠ warning emoji (the tinted call-out conveys emphasis; avoids PDF tofu)
perl -CSD -pe 's/^(\*\*(?:To|From|Date|Re):.*?)[ \t]*$/$1  /; s/\x{26A0}\x{FE0F}?[ \t]*//g;' "$IN" > "$TMP"

pandoc "$TMP" \
  --from=markdown+pipe_tables+fancy_lists+startnum+raw_attribute \
  --pdf-engine=typst \
  --pdf-engine-opt=--font-path="$FONTS" \
  --template="$TEMPLATE" \
  -V "running-head=$RUNHEAD" \
  -V "foot-note=$FOOT" \
  -o "$OUT"

echo "Memo PDF: $OUT"
