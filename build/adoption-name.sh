# Shared artifact naming for the integrated CZC, by adoption state.
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
