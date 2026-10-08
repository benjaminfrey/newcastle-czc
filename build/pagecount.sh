# Sourced by the build scripts. Defines czc_pagecount <pdf>: prints the page
# count of a PDF, and ONLY that.
#
# Callers capture it with $(...) and feed it to shell arithmetic
# (OFFSET=$((OFFSET + PAGES))) or a Typst --input. Anything else Python writes
# to STDOUT -- notably PyMuPDF's own deprecation notice for `import fitz`,
# which newer PyMuPDF prints to stdout -- becomes part of the "number", and
# under `set -u` bash then reports the first word of it as an unbound variable
# ("line N: warning: unbound variable"). Importing `pymupdf` (not `fitz`)
# removes that source; the integer check below makes any future one fail
# loudly, naming the real cause, instead of corrupting the page offset that
# every Article's verso/recto chrome is keyed to. Python's stderr is left alone
# so genuine warnings stay visible to the operator.
czc_pagecount() {
  local n
  n=$(python3 - "$1" <<'PY'
import sys, pymupdf
print(pymupdf.open(sys.argv[1]).page_count)
PY
) || return 1
  case "$n" in
    ''|*[!0-9]*)
      printf 'czc_pagecount: expected a page count for %s, got:\n%s\n' "$1" "$n" >&2
      return 1 ;;
  esac
  printf '%s\n' "$n"
}
