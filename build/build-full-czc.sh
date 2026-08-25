#!/usr/bin/env bash
# Build the full integrated CZC for a release.
#
# Each article is rendered to its own PDF (so per-article metadata — Article
# number, Article name, opener page — is honored), then all article PDFs are
# concatenated with pdfunite into a single deliverable.
#
# A cover page (baseline art + draft banner) and an auto-derived Table of
# Contents are prepended as UNNUMBERED front matter; the body keeps printing
# 1..N. The front matter is always an EVEN page count, so the body's physical
# page parity (every Article opens on a recto) is preserved. See the front-
# matter section below for the parity arithmetic.
#
# Usage:
#   build-full-czc.sh [version-tag] [date-str]
#
# DATE_STR is stamped on the cover ("Generated <date> ..."). For a reproducible
# tagged release, pass it explicitly (defaults to today, which makes rebuilds
# non-deterministic).
#
# Example:
#   build-full-czc.sh v0.1-baseline "May 30, 2026"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# SRC_DIR / OUT_DIR overrides let the formatted-redline wrapper
# (build-redline-full.sh) point this build at a staging tree of marked-up
# article markdown and write to a scratch dir — without touching source/ or a
# shipped release. Both default to the normal locations, so a plain build is
# unchanged.
SOURCE_DIR="${SRC_DIR:-$REPO_ROOT/source}"
VERSION="${1:-v0.0-dev}"
DATE_STR="${2:-$(date +"%B %-d, %Y")}"

# Adoption state. Defaults to 'draft', so every existing invocation is unchanged.
# See build/ADOPTION-SPEC.md §4.
ADOPTION_MODE="${ADOPTION_MODE:-draft}"
ADOPTION_EVENT_DATE="${ADOPTION_EVENT_DATE:-}"
case "$ADOPTION_MODE" in
  draft)    FOOTER_TEXT="Draft $VERSION" ;;
  meeting)  FOOTER_TEXT="Town Meeting Edition $VERSION" ;;
  adopted)  FOOTER_TEXT="Adopted: $ADOPTION_EVENT_DATE" ;;
  *) echo "unknown ADOPTION_MODE '$ADOPTION_MODE'" >&2; exit 1 ;;
esac
if [ "$ADOPTION_MODE" != "draft" ] && [ -z "$ADOPTION_EVENT_DATE" ]; then
  echo "ADOPTION_MODE=$ADOPTION_MODE requires ADOPTION_EVENT_DATE" >&2; exit 1
fi

BASELINE_PDF="$REPO_ROOT/docs/Newcastle Core Zoning Code.pdf"
DATA_JSON="$SOURCE_DIR/article-02-data.json"
RELEASE_DIR="${OUT_DIR:-$REPO_ROOT/releases/$VERSION}"
mkdir -p "$RELEASE_DIR"

# Collect article render units in lexical order (bash-3 compatible).
#
# Article 2 District Standards is special: its prefatory prose sections (§1-§5)
# render from markdown like every other Article (article-02-prefatory.md), but
# the 13 district SPREADS render from a native-Typst file (article-02.typ) that
# pandoc/markdown cannot express. Globbing BOTH `article-*.md` and the lone
# `article-02.typ` and sorting yields the correct interleaved order, because the
# hyphen in "article-02-prefatory.md" sorts before the dot in "article-02.typ":
#   article-01-general.md
#   article-02-prefatory.md   (Art. 2 prose  — pandoc)
#   article-02.typ            (Art. 2 spreads — typst)
#   article-03-...md ... article-09-...md
# The render loop below dispatches on extension. (The legacy hand-transcribed
# article-02-districts.md now lives in source/legacy/ and is intentionally NOT
# globbed — the district data is regenerated into article-02-data.json.)
ARTICLES=()
while IFS= read -r f; do
  ARTICLES+=("$f")
done < <(ls "$SOURCE_DIR"/article-*.md "$SOURCE_DIR"/article-02.typ 2>/dev/null | sort)

if [ ${#ARTICLES[@]} -eq 0 ]; then
  echo "No article source files found in $SOURCE_DIR" >&2
  exit 1
fi

# Working temp dir (Article-3 split-markdown halves + per-unit rendered PDFs).
TMPDIR_PDFS="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_PDFS"' EXIT

# Splice the three Article-1 District Map exhibits (native Typst,
# district-maps.typ) in AFTER Article 1's prose. The baseline closes Article 1
# with three full-page zoning exhibits (EXHIBIT 1.1 District Map, 1.2 Newcastle
# Town Center inset, 1.4 Sheepscot Village inset). They are GIS raster
# composites (vector zoning polygons over a sliced-JPEG basemap) that
# markdown/pandoc cannot express, so — exactly like the Article-2 district
# spreads (article-02.typ) and the Article-3 Type plates
# (cross-section-plates.typ) — they render natively and are concatenated in
# place. The render loop's *.typ branch threads the same cumulative even
# page-offset + footer date, so the maps' parity-aware chrome (ARTICLE 1 tab,
# GENERAL STANDARDS running head, continuous footer) is correct; the 3-page
# (odd) block is padded with one trailing blank, keeping every downstream
# Article's parity unchanged (an even shift of +4).
MAPS_TYP="$SOURCE_DIR/district-maps.typ"
if [ -f "$MAPS_TYP" ]; then
  SPLICED=()
  for f in "${ARTICLES[@]}"; do
    SPLICED+=("$f")
    case "$f" in */article-01-*.md) SPLICED+=("$MAPS_TYP") ;; esac
  done
  ARTICLES=("${SPLICED[@]}")
fi

# Splice the ten Street/Road Type pages (native Typst, cross-section-plates.typ)
# INTO Article 3 Section 2 — between the General subsection (§2.c) and the
# Driveway subsection (§2.d) — so each Type's full page sits where its standards
# live, mirroring the District pages of Article 2. Each numbered Type (S1..S5,
# R1..R5) renders as its own full page.
#
# Pandoc cannot emit a native-Typst pagebreak mid-flow, so Article 3 is rendered
# in TWO pandoc passes around the Typst block: split-article-03.py cuts the
# markdown at the <!-- TYPE-PAGES --> marker into 03a (opener + §1 + §2.a-c) and
# 03b (§2.d Driveway + §3..§14, rendered with continuation=true so the big
# "ARTICLE 3" opener is not repeated). The render order becomes [03a, plates,
# 03b]. Threading the running EVEN page offset through all three keeps footers
# continuous and every unit's parity-aware chrome (tab/header/badge) correct; the
# 10-page (EVEN) plate block preserves offset parity for the segments around it.
PLATES_TYP="$SOURCE_DIR/cross-section-plates.typ"
INV_TYP="$SOURCE_DIR/street-type-inventory.typ"          # Exhibit 3.1 (Inventory table)
MAP_TYP="$SOURCE_DIR/street-type-map.typ"                # Exhibit 3.2 (Type Map)
INVENTORY_JSON="$SOURCE_DIR/exhibits/street-types/inventory.json"
ART3_SRC=""
for f in "${ARTICLES[@]}"; do
  case "$f" in */article-03-*.md) ART3_SRC="$f" ;; esac
done
SPLIT_03A=""
SPLIT_03B=""
SPLIT_03C=""
if [ -f "$PLATES_TYP" ] && [ -n "$ART3_SRC" ]; then
  CAND_03A="$TMPDIR_PDFS/article-03a.md"
  CAND_03B="$TMPDIR_PDFS/article-03b.md"
  CAND_03C="$TMPDIR_PDFS/article-03c.md"
  if python3 "$REPO_ROOT/build/split-article-03.py" "$ART3_SRC" "$CAND_03A" "$CAND_03B" "$CAND_03C"; then
    SPLIT_03A="$CAND_03A"
    SPLIT_03B="$CAND_03B"
    # The §5 marker (when present) splits the post-plate body into 03b (§2.d..§5.C)
    # + 03c (§5.D..§14). 03c is ALWAYS spliced back so the body is never dropped;
    # the Exhibit 3.1 Inventory table + Exhibit 3.2 Type Map are inserted in front
    # of it ONLY when the real inventory.json exists (so a draft never appears until
    # promoted). Render order: [03a, plates, 03b, (inventory, map,) 03c]. The table
    # is even-paged; the 1-page map self-pads to keep §5.D verso/recto parity.
    MID=("$PLATES_TYP" "$SPLIT_03B")
    if [ -s "$CAND_03C" ]; then
      SPLIT_03C="$CAND_03C"
      if [ -f "$INVENTORY_JSON" ] && [ -f "$INV_TYP" ] && [ -f "$MAP_TYP" ]; then
        MID+=("$INV_TYP" "$MAP_TYP")
        echo "Splicing Exhibits 3.1 + 3.2 into Article 3 §5"
      fi
      MID+=("$SPLIT_03C")
    fi
    SPLICED=()
    for f in "${ARTICLES[@]}"; do
      case "$f" in
        */article-03-*.md) SPLICED+=("$SPLIT_03A" "${MID[@]}") ;;
        *) SPLICED+=("$f") ;;
      esac
    done
    ARTICLES=("${SPLICED[@]}")
  else
    # No marker (older Article 3) — fall back to appending the plate block AFTER
    # Article 3's prose, as a single pass (legacy behavior).
    echo "split-article-03: no marker; appending plate block after Article 3" >&2
    SPLICED=()
    for f in "${ARTICLES[@]}"; do
      SPLICED+=("$f")
      case "$f" in */article-03-*.md) SPLICED+=("$PLATES_TYP") ;; esac
    done
    ARTICLES=("${SPLICED[@]}")
  fi
fi

OUT_NAME="Newcastle CZC (Integrated Draft $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"
COMBINED_MD="$RELEASE_DIR/$OUT_NAME.md"

# A single blank US-Letter page, used to pad Articles that render to an odd page
# count. Padding keeps each Article opening on a recto (odd) page and keeps the
# cumulative page offset EVEN, so Typst's automatic inside/outside (binding)
# margins stay aligned with the combined document's page parity.
BLANK_PDF="$TMPDIR_PDFS/blank.pdf"
python3 - "$BLANK_PDF" <<'PY'
import sys, fitz
d = fitz.open(); d.new_page(width=612, height=792); d.save(sys.argv[1]); d.close()
PY

# Render Articles in order, threading a running page offset so footers number
# continuously across the combined document (instead of restarting at 1 per
# Article). The page COUNT of a render does not depend on the offset, so a
# single sequential pass suffices: when we render Article N the offset already
# equals the (even) page total of Articles 1..N-1.
INDEX=0
OFFSET=0
PDF_LIST=()
MD_LIST=()
for ART in "${ARTICLES[@]}"; do
  INDEX=$((INDEX + 1))
  PART="$TMPDIR_PDFS/$(printf "%02d" "$INDEX").pdf"
  # Continuous flow: no recto-opening pads. The one unit needing parity alignment is
  # article-02.typ — its 2-page district spreads must land D1 on a verso (even
  # DISPLAYED page). D1 is that unit's FIRST page, so pad to an ODD running offset
  # before it (offset+1 = even displayed page for D1). This keeps the district badges
  # on the LEFT fore-edge with NO leading blank inside the unit. (Previously this
  # padded to even AND the unit forced pagebreak(to:"even") — two redundant blanks.)
  case "$ART" in
    */article-02.typ)
      if [ $((OFFSET % 2)) -eq 0 ]; then PDF_LIST+=("$BLANK_PDF"); OFFSET=$((OFFSET + 1)); fi ;;
  esac
  case "$ART" in
    *.typ)
      # Native-Typst Article 2 district spreads. Rendered directly by typst (not
      # pandoc), threading the same cumulative even page-offset and footer date.
      # Its internal `pagebreak(to:"even")` lands the first district (D1) on a
      # verso (even) page; the surrounding even OFFSET keeps logical==physical
      # parity so the badge sits at the LEFT fore-edge. See article-02.typ.
      echo "Rendering article $INDEX (page offset $OFFSET, native Typst): $(basename "$ART")"
      # The `data=` input is read only by the §5 exhibit renderers (street-type-
      # inventory.typ / street-type-map.typ) to point at the promoted inventory;
      # the other native units ignore the extra input.
      typst compile "$ART" "$PART" \
        --font-path "$REPO_ROOT/style/fonts" \
        --input "page_offset=$OFFSET" \
        --input "footer_date=$FOOTER_TEXT" \
        --input "adoption_mode=$ADOPTION_MODE" \
        --input "data=exhibits/street-types/inventory.json"
      ;;
    *)
      # Article 3 renders in two passes (see the splice section): 03a carries the
      # opener; 03b is a continuation (opener suppressed via -V continuation). For
      # the combined-markdown reference, 03a contributes the ORIGINAL whole
      # Article 3 (its TYPE-PAGES marker swapped for a pointer note below); 03b
      # contributes nothing (already covered by the original).
      if { [ -n "$SPLIT_03B" ] && [ "$ART" = "$SPLIT_03B" ]; } || \
         { [ -n "$SPLIT_03C" ] && [ "$ART" = "$SPLIT_03C" ]; }; then
        echo "Rendering article $INDEX (page offset $OFFSET) [Art. 3 continuation]: $(basename "$ART")"
        bash "$REPO_ROOT/build/build-article.sh" "$ART" "$PART" \
          -V "footer-date=$FOOTER_TEXT" \
          -V "page-offset=$OFFSET" \
          -V "continuation=true" >/dev/null
      else
        echo "Rendering article $INDEX (page offset $OFFSET): $(basename "$ART")"
        bash "$REPO_ROOT/build/build-article.sh" "$ART" "$PART" \
          -V "footer-date=$FOOTER_TEXT" \
          -V "page-offset=$OFFSET" >/dev/null
        if [ -n "$SPLIT_03A" ] && [ "$ART" = "$SPLIT_03A" ]; then
          MD_LIST+=("$ART3_SRC")
        else
          MD_LIST+=("$ART")
        fi
      fi
      ;;
  esac
  PDF_LIST+=("$PART")
  PAGES=$(python3 - "$PART" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
)
  OFFSET=$((OFFSET + PAGES))
done

# --- Body --------------------------------------------------------------------
# Concatenate all rendered Articles into the BODY pdf. The body prints its own
# 1..N page numbers and is NOT modified by the front matter that follows.
BODY_PDF="$TMPDIR_PDFS/body.pdf"
echo "Concatenating ${#PDF_LIST[@]} PDFs ($OFFSET body pages) into body"
pdfunite "${PDF_LIST[@]}" "$BODY_PDF"

# --- Front matter (cover + auto-derived TOC) ---------------------------------
# Architecture (Convention A): front matter is UNNUMBERED; the body keeps its
# own printed 1..N. The TOC references those printed numbers, which are
# independent of front-matter length — so there is no circularity.
#
# Parity arithmetic — two invariants must hold:
#   (1) The TOC is rendered STANDALONE (its header/footer/binding margins bake
#       in at compile time keyed to its own physical page parity). For that to
#       match the final document, the number of pages BEFORE the TOC must be
#       EVEN. Cover(1) + one blank(1) = 2  ->  TOC opens on a recto, correct.
#   (2) Total front matter must be EVEN so the body's physical parity (every
#       Article opens recto) is preserved. cover+blank+TOC(+pad) is forced even
#       by padding a trailing blank when the TOC page count T is odd.
# Layout: [cover] [blank verso] [TOC ...] [blank if T odd] [body 1..N]
COVER_PDF="$TMPDIR_PDFS/cover.pdf"
TOC_JSON="$TMPDIR_PDFS/toc.json"
TOC_PDF="$TMPDIR_PDFS/toc.pdf"

echo "Building cover (baseline art + $VERSION $ADOPTION_MODE banner)"
python3 "$REPO_ROOT/build/build-cover.py" "$BASELINE_PDF" "$COVER_PDF" "$VERSION" "$DATE_STR" ${REDLINE_CAVEAT:+"$REDLINE_CAVEAT"} --mode "$ADOPTION_MODE" --event-date "$ADOPTION_EVENT_DATE"

echo "Deriving TOC entries by scanning the built body"
python3 "$REPO_ROOT/build/toc_entries.py" "$BODY_PDF" "$DATA_JSON" "$TOC_JSON"

echo "Rendering TOC"
typst compile "$REPO_ROOT/build/toc.typ" "$TOC_PDF" \
  --root / \
  --input "data=$TOC_JSON" \
  --font-path "$REPO_ROOT/style/fonts"

TOC_PAGES=$(python3 - "$TOC_PDF" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
)

# cover, blank verso, TOC, then a trailing blank iff the TOC page count is odd.
FRONT_PARTS=("$COVER_PDF" "$BLANK_PDF" "$TOC_PDF")
if [ $((TOC_PAGES % 2)) -eq 1 ]; then
  FRONT_PARTS+=("$BLANK_PDF")
fi
FRONT_COUNT=$(( 2 + TOC_PAGES + (TOC_PAGES % 2) ))

echo "Assembling: $FRONT_COUNT front-matter pages + $OFFSET body pages -> $OUTPUT_PDF"
pdfunite "${FRONT_PARTS[@]}" "$BODY_PDF" "$OUTPUT_PDF"

# Make the TOC entries clickable: add internal GoTo links from each TOC row to its
# physical page (printed body page + front-matter page count).
echo "Adding clickable TOC links"
python3 "$REPO_ROOT/build/toc_links.py" "$OUTPUT_PDF" "$FRONT_COUNT"

# Also emit the concatenated markdown source for reference (frontmatter intact;
# read by humans, not re-rendered through pandoc as one input). Only the
# markdown units are concatenated; the native-Typst district spreads have no
# markdown form, so a pointer note is injected at Article 2's position. The
# authoritative district content is article-02-data.json (rendered to the PDF).
echo "Writing combined markdown: $COMBINED_MD"
: > "$COMBINED_MD"
for ART in "${MD_LIST[@]}"; do
  case "$ART" in
    *article-03-*.md)
      # Article 3 now seats the ten Type pages INSIDE §2. Swap the TYPE-PAGES
      # build marker for a human-readable pointer note IN PLACE (between §2.c and
      # §2.d), so the combined markdown reads as the plates appear in the PDF.
      python3 - "$ART" >> "$COMBINED_MD" <<'PY'
import io, sys
with io.open(sys.argv[1], encoding="utf-8") as f:
    lines = f.read().split("\n")
note = (
    "<!-- The ten Street/Road Type pages (S1..S5, R1..R5) appear here in the\n"
    "     rendered PDF, inside Section 2 between the General subsection and the\n"
    "     Driveway subsection. Each is a full page rendered from\n"
    "     source/cross-section-plates.typ (compositing\n"
    "     source/exhibits/cross-sections/<CODE>.svg) and carries that Type's\n"
    "     description, design standards, target Districts, and character — the\n"
    "     one-stop Type page modeled on the Article 2 District pages. -->"
)
exhibits_note = (
    "<!-- Exhibit 3.1 (Inventory of Existing Streets & Roads — the binding Type\n"
    "     table) and Exhibit 3.2 (Street & Road Type Map) appear here in the\n"
    "     rendered PDF, inside Section 5 between the Inventory subsection and the\n"
    "     Classification Rubric. Both render natively from\n"
    "     source/exhibits/street-types/inventory.json (Exhibit 3.1 via\n"
    "     source/street-type-inventory.typ; 3.2 via source/street-type-map.typ). -->"
)
def swap(ln):
    if "TYPE-PAGES" in ln: return note
    if "STREET-TYPE-EXHIBITS" in ln: return exhibits_note
    return ln
sys.stdout.write("\n".join(swap(ln) for ln in lines))
PY
      ;;
    *)
      cat "$ART" >> "$COMBINED_MD"
      case "$ART" in
        *article-01-general.md)
          {
            printf '\n\n'
            printf '<!-- The three District Map exhibits (EXHIBIT 1.1 District Map, 1.2\n'
            printf '     District Map Inset - Newcastle Town Center, 1.4 District Map Inset -\n'
            printf '     Sheepscot Village) appear here in the rendered PDF as full pages. They\n'
            printf '     are GIS raster composites (vector zoning districts over an aerial\n'
            printf '     basemap) rendered natively from source/district-maps.typ (reseating\n'
            printf '     source/exhibits/district-maps/*.png). See the Integrated Draft PDF. -->\n\n'
          } >> "$COMBINED_MD"
          ;;
        *article-02-prefatory.md)
          {
            printf '\n\n'
            printf '<!-- The 13 District Standards spreads (D1-D6 + 7 Special Districts) are\n'
            printf '     rendered natively from article-02-data.json via source/article-02.typ.\n'
            printf '     See the Integrated Draft PDF for the per-district 2-page spreads. -->\n\n'
          } >> "$COMBINED_MD"
          ;;
      esac
      ;;
  esac
done

echo "Done: $OUTPUT_PDF"
