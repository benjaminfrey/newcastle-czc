#!/usr/bin/env bash
# Build the full integrated CZC for a release.
#
# Each article is rendered to its own PDF (so per-article metadata — Article
# number, Article name, opener page — is honored), then all article PDFs are
# concatenated with pdfunite into a single deliverable.
#
# Usage:
#   build-full-czc.sh [version-tag]
#
# Example:
#   build-full-czc.sh v0.1-baseline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/source"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
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

OUT_NAME="Newcastle CZC (Integrated Draft $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"
COMBINED_MD="$RELEASE_DIR/$OUT_NAME.md"

# Render each article to its own PDF.
TMPDIR_PDFS="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_PDFS"' EXIT

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
  case "$ART" in
    *.typ)
      # Native-Typst Article 2 district spreads. Rendered directly by typst (not
      # pandoc), threading the same cumulative even page-offset and footer date.
      # Its internal `pagebreak(to:"even")` lands the first district (D1) on a
      # verso (even) page; the surrounding even OFFSET keeps logical==physical
      # parity so the badge sits at the LEFT fore-edge. See article-02.typ.
      echo "Rendering article $INDEX (page offset $OFFSET, native Typst): $(basename "$ART")"
      typst compile "$ART" "$PART" \
        --font-path "$REPO_ROOT/style/fonts" \
        --input "page_offset=$OFFSET" \
        --input "footer_date=Draft $VERSION"
      ;;
    *)
      echo "Rendering article $INDEX (page offset $OFFSET): $(basename "$ART")"
      bash "$REPO_ROOT/build/build-article.sh" "$ART" "$PART" \
        -V "footer-date=Draft $VERSION" \
        -V "page-offset=$OFFSET" >/dev/null
      MD_LIST+=("$ART")
      ;;
  esac
  PDF_LIST+=("$PART")
  PAGES=$(python3 - "$PART" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
)
  # Pad odd-length Articles with a trailing blank page (keeps offsets even and
  # the next Article opening on a recto page). The final Article is never padded
  # — a trailing blank at the very end of the document serves no purpose.
  if [ $((PAGES % 2)) -eq 1 ] && [ "$INDEX" -lt "${#ARTICLES[@]}" ]; then
    PDF_LIST+=("$BLANK_PDF")
    PAGES=$((PAGES + 1))
  fi
  OFFSET=$((OFFSET + PAGES))
done

echo "Concatenating ${#PDF_LIST[@]} PDFs ($OFFSET total pages) into: $OUTPUT_PDF"
pdfunite "${PDF_LIST[@]}" "$OUTPUT_PDF"

# Also emit the concatenated markdown source for reference (frontmatter intact;
# read by humans, not re-rendered through pandoc as one input). Only the
# markdown units are concatenated; the native-Typst district spreads have no
# markdown form, so a pointer note is injected at Article 2's position. The
# authoritative district content is article-02-data.json (rendered to the PDF).
echo "Writing combined markdown: $COMBINED_MD"
: > "$COMBINED_MD"
for ART in "${MD_LIST[@]}"; do
  cat "$ART" >> "$COMBINED_MD"
  case "$ART" in
    *article-02-prefatory.md)
      {
        printf '\n\n'
        printf '<!-- The 13 District Standards spreads (D1-D6 + 7 Special Districts) are\n'
        printf '     rendered natively from article-02-data.json via source/article-02.typ.\n'
        printf '     See the Integrated Draft PDF for the per-district 2-page spreads. -->\n\n'
      } >> "$COMBINED_MD"
      ;;
  esac
done

echo "Done: $OUTPUT_PDF"
