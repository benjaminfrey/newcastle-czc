#!/usr/bin/env bash
# Build the standalone Article 3 "Streets, Roads & Driveways" deliverable.
#
# The standalone is the new Article rendered for focused review. The ten
# full-page Street/Road Type pages (S1..S5, R1..R5, native Typst from
# source/cross-section-plates.typ) are seated INSIDE Section 2 — between the
# General subsection (§2.c) and the Driveway subsection (§2.d) — mirroring the
# District pages of Article 2. Because pandoc cannot emit a native pagebreak
# mid-flow, Article 3's markdown is split at the <!-- TYPE-PAGES --> marker
# (build/split-article-03.py) into an opener segment (03a: opener + §1 + §2.a-c)
# and a continuation segment (03b: §2.d Driveway + §3..§14). The plate block sits
# between them at an EVEN page offset (padding a blank if 03a ends on an odd
# page), so every unit's parity-aware chrome (verso/recto badge + mirrored
# running head) matches its physical position and footer numbers stay continuous.
# The continuation segment is rendered with continuation:true so the big
# "ARTICLE 3" opener + divider is not repeated after the plates.
#
# Usage:
#   build-article-3.sh [version-tag]
#
# Example:
#   build-article-3.sh v0.1-draft

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/source/article-03-streets-roads-driveways.md"
PLATES_TYP="$REPO_ROOT/source/cross-section-plates.typ"
INV_TYP="$REPO_ROOT/source/street-type-inventory.typ"          # Exhibit 3.1
MAP_TYP="$REPO_ROOT/source/street-type-map.typ"                # Exhibit 3.2
INVENTORY_JSON="$REPO_ROOT/source/exhibits/street-types/inventory.json"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

if [ ! -f "$SOURCE" ]; then
  echo "Article 3 source not yet drafted: $SOURCE" >&2
  exit 1
fi

OUT_NAME="Article 3 Streets Roads & Driveways (Standalone $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"

TMPDIR_A3="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_A3"' EXIT
# Render a single Article-3 markdown segment to PDF via the CZC Typst template.
# Always stamps the Article-3 number/name (so the rotated tab and running head
# render on every segment) plus the given even page offset; extra -V args (e.g.
# continuation=true for the resumed segment) are forwarded to pandoc.
render_seg() {  # <src.md> <out.pdf> <page-offset> [extra pandoc -V ...]
  local src="$1" out="$2" off="$3"; shift 3
  pandoc "$src" \
    --from=markdown+fancy_lists+startnum \
    --pdf-engine=typst \
    --pdf-engine-opt=--font-path="$REPO_ROOT/style/fonts" \
    --template="$REPO_ROOT/style/czc-template.typ" \
    --resource-path="$REPO_ROOT/style" \
    -V article-number=3 \
    -V article-name="Streets, Roads & Driveways" \
    -V "footer-date=Draft $VERSION" \
    -V "page-offset=$off" \
    "$@" \
    -o "$out"
}

pagecount() { python3 - "$1" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
}

BLANK_PDF="$TMPDIR_A3/blank.pdf"
python3 - "$BLANK_PDF" <<'PY'
import sys, fitz
d = fitz.open(); d.new_page(width=612, height=792); d.save(sys.argv[1]); d.close()
PY

SPLIT_03A="$TMPDIR_A3/article-03a.md"
SPLIT_03B="$TMPDIR_A3/article-03b.md"
SPLIT_03C="$TMPDIR_A3/article-03c.md"
PARTS=()

if [ -f "$PLATES_TYP" ] && python3 "$REPO_ROOT/build/split-article-03.py" "$SOURCE" "$SPLIT_03A" "$SPLIT_03B" "$SPLIT_03C"; then
  # --- Type pages seated INSIDE Section 2 (two passes around the plate block) ---
  SEG_A="$TMPDIR_A3/03a.pdf"
  SEG_B="$TMPDIR_A3/03b.pdf"
  PLATES_PDF="$TMPDIR_A3/plates.pdf"

  echo "Rendering Article 3 opener segment (§1 + §2.a-c)"
  render_seg "$SPLIT_03A" "$SEG_A" 0
  PARTS+=("$SEG_A")

  # The plate block's page_offset must be EVEN (parity invariant in
  # cross-section-plates.typ). If the opener segment ends on an odd page, pad a
  # blank so the first plate opens on a recto and logical == physical for chrome.
  A_PAGES=$(pagecount "$SEG_A")
  PRECEDING=$A_PAGES
  if [ $((A_PAGES % 2)) -eq 1 ]; then
    PARTS+=("$BLANK_PDF")
    PRECEDING=$((A_PAGES + 1))
  fi

  echo "Rendering 10 Type plates (page offset $PRECEDING)"
  typst compile "$PLATES_TYP" "$PLATES_PDF" \
    --font-path "$REPO_ROOT/style/fonts" \
    --input "page_offset=$PRECEDING" \
    --input "footer_date=Draft $VERSION"
  PARTS+=("$PLATES_PDF")
  PLATES_PAGES=$(pagecount "$PLATES_PDF")

  # Continuation segment (§2.d .. §5.C when §5 exhibits splice in, else §2.d..§14)
  # at the cumulative EVEN offset.
  CONT_OFFSET=$((PRECEDING + PLATES_PAGES))
  echo "Rendering Article 3 continuation segment (page offset $CONT_OFFSET)"
  render_seg "$SPLIT_03B" "$SEG_B" "$CONT_OFFSET" -V "continuation=true"
  PARTS+=("$SEG_B")
  OFF=$((CONT_OFFSET + $(pagecount "$SEG_B")))

  # When the §5 marker split off a continuation (03c = §5.D..§14), render it — and
  # splice Exhibits 3.1 + 3.2 in front of it when the inventory data is present.
  # 03c ALWAYS renders when non-empty so the §5.D..§14 body is never dropped; only
  # the exhibits are conditional on the data existing. (Marker absent ⇒ 03c empty
  # ⇒ this whole block is skipped and SEG_B above already carries §2.d..§14.)
  if [ -s "$SPLIT_03C" ]; then
    pad_even() { if [ $((OFF % 2)) -eq 1 ]; then PARTS+=("$BLANK_PDF"); OFF=$((OFF + 1)); fi; }
    render_typ() {  # <typ> <out>  (renders at global EVEN $OFF, with the inventory data)
      typst compile "$1" "$2" --font-path "$REPO_ROOT/style/fonts" \
        --input "page_offset=$OFF" --input "footer_date=Draft $VERSION" \
        --input "data=exhibits/street-types/inventory.json"
    }
    if [ -f "$INVENTORY_JSON" ] && [ -f "$INV_TYP" ] && [ -f "$MAP_TYP" ]; then
      echo "Splicing Exhibits 3.1 + 3.2 into Article 3 §5"
      pad_even
      echo "Rendering Exhibit 3.1 Inventory table (page offset $OFF)"
      render_typ "$INV_TYP" "$TMPDIR_A3/inv.pdf"; PARTS+=("$TMPDIR_A3/inv.pdf")
      OFF=$((OFF + $(pagecount "$TMPDIR_A3/inv.pdf")))
      pad_even
      echo "Rendering Exhibit 3.2 Type Map (page offset $OFF)"
      render_typ "$MAP_TYP" "$TMPDIR_A3/map.pdf"; PARTS+=("$TMPDIR_A3/map.pdf")
      OFF=$((OFF + $(pagecount "$TMPDIR_A3/map.pdf")))
    fi
    pad_even
    echo "Rendering Article 3 continuation (§5.D-§14, page offset $OFF)"
    render_seg "$SPLIT_03C" "$TMPDIR_A3/03c.pdf" "$OFF" -V "continuation=true"
    PARTS+=("$TMPDIR_A3/03c.pdf")
  fi
else
  # Fallback: no plate file, or no marker in the source — render the whole
  # Article 3 in a single pass, appending the plate block after it if present.
  echo "Rendering Article 3 (single pass)"
  PROSE_PDF="$TMPDIR_A3/prose.pdf"
  render_seg "$SOURCE" "$PROSE_PDF" 0
  PARTS+=("$PROSE_PDF")
  if [ -f "$PLATES_TYP" ]; then
    P_PAGES=$(pagecount "$PROSE_PDF")
    PRECEDING=$P_PAGES
    if [ $((P_PAGES % 2)) -eq 1 ]; then
      PARTS+=("$BLANK_PDF")
      PRECEDING=$((P_PAGES + 1))
    fi
    PLATES_PDF="$TMPDIR_A3/plates.pdf"
    echo "Rendering 10 Type plates (page offset $PRECEDING)"
    typst compile "$PLATES_TYP" "$PLATES_PDF" \
      --font-path "$REPO_ROOT/style/fonts" \
      --input "page_offset=$PRECEDING" \
      --input "footer_date=Draft $VERSION"
    PARTS+=("$PLATES_PDF")
  fi
fi

echo "Assembling: $OUTPUT_PDF"
pdfunite "${PARTS[@]}" "$OUTPUT_PDF"

cp "$SOURCE" "$RELEASE_DIR/$OUT_NAME.md"
echo "Done: $OUTPUT_PDF"
