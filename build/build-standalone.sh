#!/usr/bin/env bash
# Unified standalone Article builder. Renders ANY CZC Article (1-9) as its own
# standalone draft PDF + markdown, for focused review — the same way Article 3
# has long been built. Native-Typst units are spliced per build/article-manifest.json:
#   Art 1 -> district-maps.typ (after the prose)
#   Art 2 -> article-02.typ district spreads (after the prose; D1 lands on a verso)
#   Art 3 -> Type plates + the two §5 exhibits, seated at markers inside the prose
# Articles with no manifest entry (4-9) render in a single pandoc pass.
#
# No cover / TOC (those are integrated-only, from build-full-czc.sh); the
# standalone numbers pages 1..N from the Article opener. The integrated CZC and
# the redline already pick up any Article's edits (they glob all source/article-*).
#
# Usage:
#   build-standalone.sh <article-NN> <version> [date-str]
# Examples:
#   build-standalone.sh 7 v0.22-draft
#   build-standalone.sh 3 v0.22-draft "June 21, 2026"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/source"
MANIFEST_PY="$REPO_ROOT/build/manifest.py"

NN_RAW="${1:-}"
VERSION="${2:-v0.0-dev}"
DATE_STR="${3:-}"        # reserved (standalone has no cover); kept for signature parity

# Adoption state, for the page footer and the §5 exhibit banners
# (street-type-inventory.typ / street-type-map.typ). Defaults to 'draft', so
# every existing invocation is unchanged. See build/ADOPTION-SPEC.md §4 / §4.2.
# Shared with build-full-czc.sh; sets FOOTER_TEXT.
source "$REPO_ROOT/build/adoption-footer.sh"

if [ -z "$NN_RAW" ]; then
  echo "usage: build-standalone.sh <article-NN> <version> [date-str]" >&2
  exit 1
fi
NN=$(printf "%02d" "$((10#$NN_RAW))")    # zero-padded "07"
NUM=$((10#$NN))                          # numeric 7

RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

# --- resolve the prose source: manifest 'prose', else glob article-0NN-*.md ----
PROSE=""
PRO=$(python3 "$MANIFEST_PY" prose "$NUM" 2>/dev/null || true)
if [ -n "$PRO" ]; then
  PROSE="$SOURCE_DIR/$PRO"
else
  for f in "$SOURCE_DIR"/article-"$NN"-*.md; do
    [ -f "$f" ] && PROSE="$f" && break
  done
fi
if [ -z "$PROSE" ] || [ ! -f "$PROSE" ]; then
  echo "No prose source for Article $NUM (manifest 'prose' or source/article-$NN-*.md)" >&2
  exit 1
fi

# --- article number/name from frontmatter (for the output filename) ------------
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
ANUM=$(read_meta "$PROSE" article-number); ANUM="${ANUM:-$NUM}"
ANAME=$(read_meta "$PROSE" article-name);  ANAME="${ANAME:-Article $NUM}"

OUT_NAME="Article $ANUM $ANAME (Standalone $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

pagecount() { python3 - "$1" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
}

BLANK_PDF="$TMP/blank.pdf"
python3 - "$BLANK_PDF" <<'PY'
import sys, fitz
d = fitz.open(); d.new_page(width=612, height=792); d.save(sys.argv[1]); d.close()
PY

# Render one prose segment via the generic primitive. article-number/name come
# from the markdown frontmatter; we override footer-date to the adoption-mode
# footer text (see adoption-footer.sh) and thread the running page offset.
# Extra -V args (e.g. continuation=true) pass through.
render_seg() {  # <src.md> <out.pdf> <page-offset> [extra -V ...]
  local src="$1" out="$2" off="$3"; shift 3
  bash "$REPO_ROOT/build/build-article.sh" "$src" "$out" \
    -V "footer-date=$FOOTER_TEXT" -V "page-offset=$off" "$@" >/dev/null
}

PARTS=()
OFF=0

# Render every manifest unit whose `splice` equals $1, threading the running
# offset (and the Art-2 pad-to-odd parity guard). Skips a unit whose
# conditional_on path is absent. Mutates the globals PARTS and OFF.
render_units_matching() {  # <splice-value>
  local want="$1" typ splice data cond parity pad out
  while IFS='|' read -r typ splice data cond parity pad; do
    [ -z "$typ" ] && continue
    [ "$splice" != "$want" ] && continue
    if [ -n "$cond" ] && [ ! -f "$SOURCE_DIR/$cond" ]; then
      echo "  (skipping $typ — $cond absent)"; continue
    fi
    if [ "$parity" = "pad-to-odd-before" ] && [ $((OFF % 2)) -eq 0 ]; then
      PARTS+=("$BLANK_PDF"); OFF=$((OFF + 1))   # pad so the unit's first page is a verso (e.g. Art-2 D1)
    fi
    out="$TMP/unit-${#PARTS[@]}.pdf"
    local args=( --font-path "$REPO_ROOT/style/fonts"
                 --input "page_offset=$OFF" --input "footer_date=$FOOTER_TEXT"
                 --input "adoption_mode=$ADOPTION_MODE" )
    [ -n "$data" ] && args+=( --input "data=$data" )
    echo "Rendering $typ (page offset $OFF)"
    typst compile "$SOURCE_DIR/$typ" "$out" "${args[@]}"
    PARTS+=("$out"); OFF=$((OFF + $(pagecount "$out")))
    # pad_to=even-block only matters mid-document; standalone units of this kind
    # (Art-1 maps) are last, so a trailing pad would just dangle — intentionally skipped.
  done < <(python3 "$MANIFEST_PY" units "$NUM")
}

if python3 "$MANIFEST_PY" has "$NUM" 2>/dev/null; then
  MARKERS=$(python3 "$MANIFEST_PY" markers "$NUM" 2>/dev/null || true)
  if [ -n "$MARKERS" ]; then
    # ---- at-marker splice path (Article 3: two markers, units interleaved) ----
    read -r M1 M2 <<< "$MARKERS"
    SEG_A="$TMP/seg-a.md"; SEG_B="$TMP/seg-b.md"; SEG_C="$TMP/seg-c.md"
    if ! python3 "$REPO_ROOT/build/split-article-03.py" "$PROSE" "$SEG_A" "$SEG_B" "$SEG_C"; then
      echo "split failed for Article $NUM ($PROSE)" >&2; exit 1
    fi
    echo "Rendering Article $NUM opener segment"
    render_seg "$SEG_A" "$TMP/a.pdf" 0; PARTS+=("$TMP/a.pdf"); OFF=$(pagecount "$TMP/a.pdf")
    render_units_matching "at-marker:$M1"
    echo "Rendering Article $NUM continuation (page offset $OFF)"
    render_seg "$SEG_B" "$TMP/b.pdf" "$OFF" -V "continuation=true"
    PARTS+=("$TMP/b.pdf"); OFF=$((OFF + $(pagecount "$TMP/b.pdf")))
    if [ -s "$SEG_C" ]; then
      [ -n "$M2" ] && render_units_matching "at-marker:$M2"
      echo "Rendering Article $NUM continuation (page offset $OFF)"
      render_seg "$SEG_C" "$TMP/c.pdf" "$OFF" -V "continuation=true"
      PARTS+=("$TMP/c.pdf"); OFF=$((OFF + $(pagecount "$TMP/c.pdf")))
    fi
  else
    # ---- after-prose splice path (Art 1 maps, Art 2 spreads) ----
    echo "Rendering Article $NUM ($ANAME) prose"
    render_seg "$PROSE" "$TMP/prose.pdf" 0; PARTS+=("$TMP/prose.pdf"); OFF=$(pagecount "$TMP/prose.pdf")
    render_units_matching "after-prose"
  fi
else
  # ---- pure-prose fast path (Art 4-9) ----
  echo "Rendering Article $NUM ($ANAME) — single pass"
  render_seg "$PROSE" "$TMP/prose.pdf" 0; PARTS+=("$TMP/prose.pdf")
fi

echo "Assembling: $OUTPUT_PDF"
pdfunite "${PARTS[@]}" "$OUTPUT_PDF"
cp "$PROSE" "$RELEASE_DIR/$OUT_NAME.md"
echo "Done: $OUTPUT_PDF ($(pagecount "$OUTPUT_PDF") pages)"
