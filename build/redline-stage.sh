# Stage a redline's NEW side and mark its old side, for one Article or all of them.
#
# THE RETURN-CODE CONTRACT LIVES HERE AND NOWHERE ELSE. build/redline_resolve.py
# distinguishes three outcomes, and the difference between them is the
# difference between a correct redline and one reporting the whole Code as
# newly written (build/adoption_map.py:6-9 records that measured failure):
#   rc 0  the old side was written
#   rc 3  the article is NEW at this adoption -> empty old side, whole body
#         marked as added. Correct here and only here.
#   rc 4  the article is NOT TEXT-COMPARABLE -> old copied from new, so it
#         renders UNMARKED. Its content moved into a native-Typst unit between
#         the baseline and now, and a text diff would show phantom deletions.
#   else  refuse. Rendering it as new would misrepresent the Code.
#
# Sourced (not executed), beside build/adoption-footer.sh.
#
#   czc_redline_stage <src-dir> <stage-dir> <old-ver> <baseline-flag> <plain-flag> [basename ...]
#
# With no basenames, every article-*.md in the stage is marked. The NEW side is
# never normalised: it is the document being published. Only the OLD side may be
# normalised for rendering (see build/normalize_for_diff.py's module docstring).
#
# <plain-flag> is "" or "--plain". PLAIN OUTPUT IS FOR A PUBLISHED .md ONLY: it
# carries a "Redline key:" legend at the head of every marked file (even one
# with zero changes) and a sigil on whole-line insertions, and --source writes
# it OVER the staged article. Typeset, that is nine legends and every sigil in a
# document the Town binds -- and nothing downstream would object (pandoc renders
# it cleanly, the front-matter still parses, "Redline key:" is not a chrome
# string for the residue gate). So a plain-marked stage is LABELLED with
# $CZC_PLAIN_MARK_FILE, and build-full-czc.sh and build-standalone.sh (via
# adoption-footer.sh) refuse any SRC_DIR that carries the label.
CZC_PLAIN_MARK_FILE=".redline-plain-marked"

czc_redline_stage() {
  local src="$1" stage="$2" old_ver="$3" baseline_flag="$4" plain_flag="$5"
  shift 5
  local repo_root; repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local redline_py="$repo_root/build/redline-text.py"

  mkdir -p "$stage"
  cp -R "$src/." "$stage/"
  if [ -n "$plain_flag" ]; then
    printf '%s\n' "This tree was marked with redline-text.py $plain_flag. It is for a published .md, never for a PDF build." \
      > "$stage/$CZC_PLAIN_MARK_FILE"
  fi

  local -a bases=()
  if [ $# -gt 0 ]; then
    bases=("$@")
  else
    local f
    for f in "$stage"/article-*.md; do
      [ -f "$f" ] && bases+=("$(basename "$f")")
    done
  fi

  local oldtmp; oldtmp="$(mktemp)"
  local n=0 base nf rc
  # ${arr[@]+...}: an empty array is "unbound" under `set -u` in bash 3.2.
  for base in ${bases[@]+"${bases[@]}"}; do
    nf="$stage/$base"
    if [ ! -f "$nf" ]; then
      echo "redline: no such article in the stage: $base" >&2
      rm -f "$oldtmp"; return 1
    fi
    # Every branch below must (re)create oldtmp. Removing it first means a
    # branch that fails to do so is caught by the existence check rather than
    # silently reusing the previous article's old side.
    rm -f "$oldtmp"
    # `|| rc=$?` captures the exit status without toggling `set -e` in the
    # caller's shell (this file is sourced).
    rc=0
    python3 "$repo_root/build/redline_resolve.py" "$base" "$old_ver" "$oldtmp" $baseline_flag || rc=$?
    case "$rc" in
      0) ;;
      3) : > "$oldtmp"
         echo "  ($base is new since $old_ver — whole body marked as added)" ;;
      4) cp "$nf" "$oldtmp"
         echo "  ($base is not text-comparable against $old_ver — rendered unmarked)" ;;
      *) echo "redline: could not resolve the old side for $base (exit $rc)." >&2
         rm -f "$oldtmp"; return 1 ;;
    esac
    if [ ! -e "$oldtmp" ]; then
      echo "redline: internal error — no old side was produced for $base (exit $rc)." >&2
      rm -f "$oldtmp"; return 1
    fi
    python3 "$redline_py" "$oldtmp" "$nf" "$nf" --source $plain_flag || { rm -f "$oldtmp"; return 1; }
    n=$((n + 1))
  done
  rm -f "$oldtmp"
  echo "Marked $n article markdown file(s) (vs $old_ver)."
}
