#!/usr/bin/env python3
"""Split Article 3 at the <!-- TYPE-PAGES --> marker into two pandoc passes.

Article 3 seats the ten native-Typst Street/Road Type pages INSIDE Section 2,
between the General subsection (§2.c) and the Driveway subsection (§2.d) — so
each Type's full page sits where its standards live, mirroring the District
pages of Article 2. Pandoc cannot emit a native-Typst pagebreak mid-flow, so the
build renders Article 3 in TWO pandoc passes around the Typst plate block:

  <out-03a.md>  original frontmatter + body BEFORE the marker
                (the "ARTICLE 3" opener + §1 General + §2.a-§2.c)
  <out-03b.md>  frontmatter + body AFTER the marker
                (§2.d Driveway + §3 .. §14)

03b's frontmatter gets ``continuation: true`` so the CZC template suppresses the
big "ARTICLE 3" opener + divider on the resumed segment; the rotated Article tab
and the running head still render (they key off article-number / article-name,
which the split preserves on both halves). The marker line itself is dropped.

Usage:
  split-article-03.py <article-03.md> <out-03a.md> <out-03b.md>

Exit status:
  0  split written
  1  bad arguments
  2  no marker line found (caller may fall back to a single-pass render)
"""
import io
import sys

MARKER = "TYPE-PAGES"            # §2: split before the ten Type plates
MARKER2 = "STREET-TYPE-EXHIBITS"  # §5.C: split before the Inventory + Type-Map exhibits


def _find(body, marker):
    for i, ln in enumerate(body):
        if marker in ln:
            return i
    return None


def _cont(frontmatter):
    fm = list(frontmatter)
    if fm:
        fm.insert(len(fm) - 1, "continuation: true\n")   # before the closing '---'
    else:
        fm = ["---\n", "continuation: true\n", "---\n"]
    return fm


def main():
    args = sys.argv[1:]
    if len(args) not in (3, 4):
        sys.stderr.write("usage: split-article-03.py <in.md> <out-03a.md> <out-03b.md> [<out-03c.md>]\n")
        return 1
    src, out_a, out_b = args[0], args[1], args[2]
    out_c = args[3] if len(args) == 4 else None

    with io.open(src, encoding="utf-8") as f:
        lines = f.readlines()

    # Parse a leading YAML frontmatter block delimited by '---' lines, if any.
    frontmatter = []
    body = lines
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                frontmatter = lines[: i + 1]
                body = lines[i + 1 :]
                break

    m1 = _find(body, MARKER)
    if m1 is None:
        sys.stderr.write("split-article-03: no %s marker found in %s\n" % (MARKER, src))
        return 2
    before, after = body[:m1], body[m1 + 1:]

    # 03a: original frontmatter + everything before the §2 plate marker.
    with io.open(out_a, "w", encoding="utf-8") as f:
        f.writelines(frontmatter)
        f.writelines(before)

    fm_cont = _cont(frontmatter)

    # Optional second split at the §5 exhibit marker (only if an out-c path is
    # given AND the marker exists). Otherwise 03b is everything after the plates
    # and out-c (if given) is written empty so callers can detect "no 2nd split".
    m2 = _find(after, MARKER2) if out_c else None
    if out_c and m2 is not None:
        before2, after2 = after[:m2], after[m2 + 1:]
        with io.open(out_b, "w", encoding="utf-8") as f:
            f.writelines(fm_cont)
            f.writelines(before2)
        with io.open(out_c, "w", encoding="utf-8") as f:
            f.writelines(fm_cont)
            f.writelines(after2)
    else:
        with io.open(out_b, "w", encoding="utf-8") as f:
            f.writelines(fm_cont)
            f.writelines(after)
        if out_c:
            io.open(out_c, "w", encoding="utf-8").close()   # empty => no 2nd split

    return 0


if __name__ == "__main__":
    sys.exit(main())
