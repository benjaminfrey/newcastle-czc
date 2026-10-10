# Article metadata helpers shared by the standalone builders.
#
# Sourced (not executed), beside build/adoption-name.sh, by build-standalone.sh and
# build-redline-standalone.sh, so the two read ONE definition of "which file is
# Article N's prose" and "what does its frontmatter say". A second copy is how the
# redline would come to name, or stage, a different file than the build it feeds.
#
#   czc_article_prose <src-dir> <article-num>
#       The prose file's BASENAME: the manifest's `prose` for the Article, else the
#       first article-0NN-*.md in <src-dir>. Returns 1 (printing nothing) when
#       there is none, or when the named file is not in <src-dir>.
#   czc_read_meta <file> <key>
#       The value of a frontmatter key, unquoted, or the empty string.
czc_article_prose() {
  local src="$1" num=$((10#$2)) nn pro f
  nn=$(printf "%02d" "$num")
  local repo_root; repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  pro=$(python3 "$repo_root/build/manifest.py" prose "$num" 2>/dev/null || true)
  if [ -z "$pro" ]; then
    for f in "$src"/article-"$nn"-*.md; do
      [ -f "$f" ] && pro="$(basename "$f")" && break
    done
  fi
  if [ -z "$pro" ] || [ ! -f "$src/$pro" ]; then
    return 1
  fi
  printf '%s\n' "$pro"
}

czc_read_meta() { python3 - "$1" "$2" <<'PY'
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
