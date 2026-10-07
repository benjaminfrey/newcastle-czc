# Shared artifact naming for the integrated CZC and its per-Article standalones,
# by adoption state.
#
# THE FILENAME IS CHROME TOO. A Town Meeting edition filed as
# "Newcastle CZC (Integrated Draft v1.0).pdf" is the file a voter downloads
# from the warrant packet: its cover says TOWN MEETING EDITION and its
# filename says Integrated Draft. Adopted mode was fixed for exactly this
# reason in Task 8 (build/adopted_residue.py checks filenames, not just page
# text); the meeting mode was left one mode short and is fixed here.
#
# Sourced (not executed) by build-full-czc.sh, build-redline-full.sh,
# build-adoption.sh and build-adopted.sh so that the producer and every
# consumer read one definition. Pure function, no globals, no dependence on
# the caller's cwd.
#
#   czc_integrated_name <draft|meeting|adopted> <version>
czc_integrated_name() {
  case "$1" in
    draft)   printf 'Newcastle CZC (Integrated Draft %s)' "$2" ;;
    meeting) printf 'Newcastle CZC (Town Meeting Edition %s)' "$2" ;;
    adopted) printf 'Newcastle CZC (Adopted %s)' "$2" ;;
    *) echo "czc_integrated_name: unknown adoption mode '$1'" >&2; return 1 ;;
  esac
}

#   czc_standalone_name <draft|meeting|adopted> <article-num> <article-name> <version> [redline]
#
# The per-Article extract's name. Composed inline at build-standalone.sh:83,
# which this replaces; that composition had no mode component, which left three
# consumers disagreeing: build-adoption.sh hard-coded one article's filename, and
# test_footer_modes.py globbed "Article N *.pdf" and took whichever matched
# first -- which matches a standalone AND its redline.
#
# Any non-empty fifth argument selects the redline form. Standalones do not
# ship with an adoption release (decision D5), but build-adoption.sh builds one
# today, so all three modes are defined.
czc_standalone_name() {
  local mode="$1" anum="$2" aname="$3" version="$4" redline="${5:-}"
  local stem
  case "$mode" in
    draft)   stem="Article $anum $aname (Standalone $version)" ;;
    meeting) stem="Article $anum $aname (Standalone Town Meeting Edition $version)" ;;
    adopted) stem="Article $anum $aname (Standalone Adopted $version)" ;;
    *) echo "czc_standalone_name: unknown adoption mode '$mode'" >&2; return 1 ;;
  esac
  if [ -n "$redline" ]; then
    printf '%s — Redline' "$stem"
  else
    printf '%s' "$stem"
  fi
}
