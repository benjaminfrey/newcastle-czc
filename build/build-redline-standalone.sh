#!/usr/bin/env bash
# Standalone redline of ONE Article -- the per-Article counterpart of
# build-redline-full.sh, and the deliverable standing rule 4 asks for beside every
# Article that changed in substance: a .pdf AND a .md.
#
# It composes seams that already exist:
#   * redline-stage.sh marks the Article's prose against the old version, TWICE
#     from the same source -- Typst-marked for the PDF (additions red, deletions
#     struck) and --plain for the markdown (additions **bold**, deletions ~~struck~~).
#     A plain stage is never typeset (adoption-footer.sh refuses one), hence two.
#   * structural_note.py --scope article:N writes this Article's "How to read this
#     redline" page (PDF and markdown), padded to an EVEN page count.
#   * build-standalone.sh builds the Article with that page as uncounted front
#     matter (STANDALONE_FRONT_NOTE; even, so every footer keeps its physical
#     page's verso/recto parity), under the redline's name (OUT_NAME_OVERRIDE),
#     and ships the plain-marked markdown, with the page inserted after its
#     legend, as the .md (OUT_MD_SOURCE).
#
# Usage:
#   build-redline-standalone.sh <article-NN> <new-ver> <old-ver> [date-str]
#     <new-ver>  labels the output; the NEW content is $SRC_DIR (default source/)
#     <old-ver>  git ref compared against
#
# Environment (each defaults to the ordinary draft behaviour):
#   SRC_DIR            the NEW tree                       (default: $REPO_ROOT/source)
#   ADOPTION_BASELINE  1 = compare against the previously adopted Code (adoption-map.json)
#   ADOPTION_MODE / ADOPTION_EVENT_DATE   chrome mode, through build-standalone.sh
#   REDLINE_OUT        a DIRECTORY; both files go there and releases/ is not touched
#
# Output: <Article N Name (Standalone <ver>) — Redline>.pdf and .md in
#   releases/<new-ver>/ (or $REDLINE_OUT). Every refusal happens before anything
#   is placed, so a refused run leaves no output directory.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${SRC_DIR:-$REPO_ROOT/source}"

NN_RAW="${1:-}"
NEW_V="${2:-}"
OLD_V="${3:-}"
DATE_STR="${4:-$(date +"%B %-d, %Y")}"

if [ -z "$NN_RAW" ] || [ -z "$NEW_V" ] || [ -z "$OLD_V" ]; then
  echo "usage: build-redline-standalone.sh <article-NN> <new-ver> <old-ver> [date-str]" >&2
  exit 1
fi
NUM=$((10#$NN_RAW))
NN=$(printf "%02d" "$NUM")

BASELINE_FLAG=""
if [ "${ADOPTION_BASELINE:-0}" = "1" ]; then BASELINE_FLAG="--baseline"; fi

# --- the prose basename, resolved exactly as build-standalone.sh does ----------
PRO=$(python3 "$REPO_ROOT/build/manifest.py" prose "$NUM" 2>/dev/null || true)
if [ -z "$PRO" ]; then
  for f in "$SRC"/article-"$NN"-*.md; do
    [ -f "$f" ] && PRO="$(basename "$f")" && break
  done
fi
if [ -z "$PRO" ] || [ ! -f "$SRC/$PRO" ]; then
  echo "redline-standalone: no prose source for Article $NUM in $SRC" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

source "$REPO_ROOT/build/redline-stage.sh"
source "$REPO_ROOT/build/adoption-name.sh"
source "$REPO_ROOT/build/pagecount.sh"

echo "Standalone redline: Article $NUM, NEW = $SRC (labeled $NEW_V)   vs   OLD = $OLD_V"

# --- 1. stage the one Article twice: Typst-marked (PDF) and plain-marked (.md) --
czc_redline_stage "$SRC" "$TMP/stage" "$OLD_V" "$BASELINE_FLAG" "" "$PRO" \
  || { echo "redline-standalone: staging the PDF side failed." >&2; exit 1; }
czc_redline_stage "$SRC" "$TMP/plain" "$OLD_V" "$BASELINE_FLAG" "--plain" "$PRO" \
  || { echo "redline-standalone: staging the markdown side failed." >&2; exit 1; }

# --- 2. the "How to read this redline" page (PDF + markdown), even length -------
python3 "$REPO_ROOT/build/structural_note.py" "$TMP/note.pdf" \
  --scope "article:$NUM" --old "$OLD_V" --new-dir "$SRC" \
  --md "$TMP/note.md" --pad-to-even \
  || { echo "redline-standalone: could not write the disclosure page." >&2; exit 1; }

# --- 3. the .md deliverable: plain-marked prose + the page after its legend -----
python3 - "$TMP/plain/$PRO" "$TMP/note.md" "$TMP/redline.md" <<'PY' \
  || { echo "redline-standalone: could not assemble the markdown redline." >&2; exit 1; }
import re, sys
src, note, out = sys.argv[1:4]
text = open(src, encoding="utf-8").read()
note_md = open(note, encoding="utf-8").read().strip("\n")
m = re.match(r"^---\n.*?\n---\n", text, re.S)
front = m.group(0) if m else ""
rest = text[len(front):].lstrip("\n")
legend, sep, body = rest.partition("\n\n")
parts = [front.rstrip("\n"), "", legend, "", note_md, "", body.lstrip("\n")] if front else \
        [legend, "", note_md, "", body.lstrip("\n")]
open(out, "w", encoding="utf-8").write("\n".join(parts).rstrip("\n") + "\n")
PY

# --- 4. the name, from the Article's own frontmatter ---------------------------
read_meta() { python3 - "$1" "$2" <<'PY'
import sys, re
txt = open(sys.argv[1], encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---", txt, re.S)
key, val = sys.argv[2], ""
if m:
    for ln in m.group(1).split("\n"):
        if ln.startswith(key + ":"):
            val = ln.split(":", 1)[1].strip().strip('"')
            break
print(val)
PY
}
ANUM=$(read_meta "$SRC/$PRO" article-number); ANUM="${ANUM:-$NUM}"
ANAME=$(read_meta "$SRC/$PRO" article-name);  ANAME="${ANAME:-Article $NUM}"
NAME="$(czc_standalone_name "${ADOPTION_MODE:-draft}" "$ANUM" "$ANAME" "$NEW_V" redline)"

# --- 5. build through the standalone builder -----------------------------------
SRC_DIR="$TMP/stage" OUT_DIR="$TMP/out" OUT_NAME_OVERRIDE="$NAME" \
  STANDALONE_FRONT_NOTE="$TMP/note.pdf" OUT_MD_SOURCE="$TMP/redline.md" \
  bash "$REPO_ROOT/build/build-standalone.sh" "$NN" "$NEW_V" "$DATE_STR"

if [ ! -f "$TMP/out/$NAME.pdf" ] || [ ! -f "$TMP/out/$NAME.md" ]; then
  echo "redline-standalone: the build did not produce the expected files for '$NAME'." >&2
  exit 1
fi

# --- 6. place -------------------------------------------------------------------
DEST="${REDLINE_OUT:-$REPO_ROOT/releases/$NEW_V}"
mkdir -p "$DEST"
mv "$TMP/out/$NAME.pdf" "$DEST/$NAME.pdf"
mv "$TMP/out/$NAME.md" "$DEST/$NAME.md"
echo "Standalone redline saved ($(czc_pagecount "$DEST/$NAME.pdf") pages):"
echo "  $DEST/$NAME.pdf"
echo "  $DEST/$NAME.md"
