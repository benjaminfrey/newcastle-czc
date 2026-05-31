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

MARKER = "TYPE-PAGES"


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(
            "usage: split-article-03.py <in.md> <out-03a.md> <out-03b.md>\n"
        )
        return 1
    src, out_a, out_b = sys.argv[1], sys.argv[2], sys.argv[3]

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

    # Locate the marker line within the body.
    marker_idx = None
    for i, ln in enumerate(body):
        if MARKER in ln:
            marker_idx = i
            break
    if marker_idx is None:
        sys.stderr.write("split-article-03: no %s marker found in %s\n" % (MARKER, src))
        return 2

    before = body[:marker_idx]
    after = body[marker_idx + 1 :]

    # 03a: original frontmatter + everything before the marker.
    with io.open(out_a, "w", encoding="utf-8") as f:
        f.writelines(frontmatter)
        f.writelines(before)

    # 03b: frontmatter with `continuation: true` added + everything after.
    fm_b = list(frontmatter)
    if fm_b:
        # frontmatter == ['---\n', ...keys..., '---\n']; insert before the close.
        fm_b.insert(len(fm_b) - 1, "continuation: true\n")
    else:
        fm_b = ["---\n", "continuation: true\n", "---\n"]
    with io.open(out_b, "w", encoding="utf-8") as f:
        f.writelines(fm_b)
        f.writelines(after)

    return 0


if __name__ == "__main__":
    sys.exit(main())
