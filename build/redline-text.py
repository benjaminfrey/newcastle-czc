#!/usr/bin/env python3
"""Generate a TEXT redline (as markdown) between two versions of a document.

Deletions are wrapped in markdown strikeout (``~~ ... ~~``); insertions are
wrapped in a raw-Typst red inline span and placed immediately AFTER the struck
text. The emitted markdown renders through

    pandoc --pdf-engine=typst --template=style/redline-template.typ

to a compact *vector* PDF — kilobytes, not the 100 MB raster overlay that
``diff-pdf`` produced.

Only TEXT is compared. The integrated ``.md`` deliverable carries every
Article's prose; the native-Typst units (Article 2 district spreads, the
Article 3 Type plates, the Article 1 district maps) and their PNGs live in
``.typ`` / image files and never appear in the markdown — so layout-only and
image-only changes are ignored by construction, which is exactly what a text
redline should do.

Usage:
    redline-text.py <old.md> <new.md> <out.md>

Diff granularity:
  * Fenced blocks (``` ... ``` / ``` ```{=typst} ``` raw Typst tables, code) are
    masked to a single content-hashed token BEFORE diffing, so they are compared
    atomically and never have markdown markup injected into them (which would
    corrupt the Typst they emit). An unchanged block renders verbatim; a
    changed/added block renders verbatim with a small red note; a removed block
    leaves a struck note.
  * Prose: a line-level pass (difflib) classifies runs as equal / delete /
    insert / replace. A 1-to-1 ``replace`` is refined to a WORD-level diff so
    only the changed words inside a line are marked (the shared leading block
    marker — heading ``#``, list number, blockquote ``>`` — is preserved so the
    line still parses as that block). Multi-line ``replace`` strikes the old
    block then adds the new block.
  * Pipe-table rows (``| ... |``) are marked at the CELL level so the row keeps
    its ``|`` delimiters and still parses as a table.
"""
import os
import sys
import re
import hashlib
import difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import structure_text  # noqa: E402  (plain-words names; shared with the disclosure page)

# Red used for additions. Matches the legend in style/redline-template.typ.
RED = '#text(fill: rgb("#cc0000"))'

# Sentinel prefix for a masked fenced block (private-use area, won't occur in text).
BLOCK_TOKEN = 'BLK'

# Opening/closing fence of a code or raw block.
FENCE_RE = re.compile(r'^[ \t]*(`{3,}|~{3,})')

# Leading markdown block syntax to keep OUTSIDE the strike/red wrapper so the
# line still parses as a heading / list item / blockquote after marking.
PREFIX_RE = re.compile(
    r'^(\s*(?:#{1,6}[ \t]+|>[ \t]?|[-*+][ \t]+|\d+\.[ \t]+|[A-Za-z]\.[ \t]+'
    r'|[ivxlcdmIVXLCDM]+\.[ \t]+)?)(.*)$',
    re.S,
)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def strip_meta(text: str) -> str:
    """Remove non-content noise so it never shows up as a phantom change.

    * Per-article YAML front-matter blocks (``--- key: val ... ---``) — the
      integrated deliverable concatenates one per Article; they are metadata.
    * HTML comments (e.g., the district-map placeholder note) — they do not
      render, so a comment-only delta must not appear in the redline.
    """
    text = re.sub(r'(?m)^---[ \t]*\n(?:[^\n]*:[^\n]*\n)+---[ \t]*\n?', '', text)
    text = re.sub(r'(?s)<!--.*?-->[ \t]*\n?', '', text)
    return text


# Article 2's per-District spreads — the Core Districts (``## D1`` … ``## D6``)
# and the Special Districts (``## SD …``). In current releases these live in
# source/article-02-data.json and render as native-Typst 2-page spreads; they
# are NOT in the markdown. The v0.1 baseline, however, authored every District
# as markdown prose and tables (use matrices, lot-dimension tables, ~2,300
# lines), so a naive text diff against the baseline reports them as a wall of
# phantom "deletions" even though nothing was deleted — the content only moved
# to native rendering. Honoring this tool's contract (native layout is not
# text-compared), drop these sections from BOTH documents. This is a no-op for
# post-migration draft-to-draft redlines (neither side carries them).
NATIVE_SECTION_RE = re.compile(r'^##[ \t]+(?:D[1-6]\b|SD[ \t]+\S)')


def drop_native_sections(text: str) -> str:
    """Remove H2 District-spread sections that migrated to native rendering.

    Skipping runs from a matching ``##`` heading up to (not including) the next
    H1/H2 heading, so the District's own ``###``/``####`` subsections are
    dropped with it while the general prose sections (``## 1. DISTRICTS`` …
    ``## 5. CIVIC DISTRICT``) and every later Article are preserved.
    """
    out, skip = [], False
    for ln in text.split('\n'):
        if re.match(r'^#{1,2}[ \t]', ln):      # H1 or H2 boundary re-evaluates
            skip = bool(NATIVE_SECTION_RE.match(ln))
        if not skip:
            out.append(ln)
    return '\n'.join(out)


def prepare(text: str):
    """Normalise → drop native spreads → mask fenced blocks. Returns
    ``(lines, registry)`` ready to diff."""
    return mask_blocks(drop_native_sections(strip_meta(text)))


def mask_blocks(text: str):
    """Replace each fenced block with a single content-hashed token line.

    Returns (lines, registry) where ``lines`` is the line list with blocks
    collapsed to tokens, and ``registry`` maps token -> verbatim block text.
    Identical block content yields the same token (so unchanged blocks compare
    equal); differing content yields different tokens (so the diff sees a
    change) without ever splitting the block across diff opcodes.
    """
    lines = text.split('\n')
    out = []
    registry = {}
    i, n = 0, len(lines)
    while i < n:
        m = FENCE_RE.match(lines[i])
        if m:
            fence_char = m.group(1)[0]
            open_len = len(m.group(1))
            close_re = re.compile(r'^[ \t]*' + re.escape(fence_char) + '{' + str(open_len) + r',}[ \t]*$')
            block = [lines[i]]
            i += 1
            while i < n:
                block.append(lines[i])
                closed = close_re.match(lines[i])
                i += 1
                if closed:
                    break
            content = '\n'.join(block)
            token = BLOCK_TOKEN + hashlib.sha1(content.encode('utf-8')).hexdigest()
            registry[token] = content
            out.append(token)
        else:
            out.append(lines[i])
            i += 1
    return out, registry


def is_block_token(ln: str) -> bool:
    return ln.startswith(BLOCK_TOKEN)


# ---------------------------------------------------------------------------
# Inline wrappers
# ---------------------------------------------------------------------------

def typ_lit(s: str) -> str:
    """Escape a literal string for Typst content mode inside ``#text[ ... ]``."""
    return re.sub(r'([\\#\[\]$*_@<~])', r'\\\1', s)


def typ_str(s: str) -> str:
    """Quote ``s`` as a Typst string literal (for e.g. ``#raw(...)``)."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


# Markdown inline emphasis, tried longest-delimiter-first so ``**`` is consumed
# before single ``*``. Word-boundary guards keep stray ``*``/``_`` in
# identifiers from triggering a false emphasis run.
_INLINE_RE = re.compile(
    r'\*\*(?P<b1>.+?)\*\*'                     # **bold**
    r'|__(?P<b2>.+?)__'                        # __bold__
    r'|(?<![\w*])\*(?P<i1>[^*\s](?:.*?[^*\s])?)\*(?![\w*])'  # *italic*
    r'|(?<![\w_])_(?P<i2>[^_\s](?:.*?[^_\s])?)_(?![\w_])'    # _italic_
    r'|`(?P<code>[^`]+)`'                      # `code`
)


def md_inline_to_typ(s: str) -> str:
    """Convert a markdown inline string to Typst content-mode markup for use
    inside ``#text(fill: ...)[ ... ]``.

    Bold/italic/inline-code become Typst function calls (``#strong``/``#emph``/
    ``#raw``) so *added* text renders formatted instead of showing literal
    ``**`` / ``_`` characters; every other character is escaped to literal
    Typst. Unmatched/odd delimiters simply fall through to ``typ_lit`` — never a
    compile error."""
    out, pos = [], 0
    for m in _INLINE_RE.finditer(s):
        if m.start() > pos:
            out.append(typ_lit(s[pos:m.start()]))
        if m.group('b1') is not None or m.group('b2') is not None:
            out.append(f'#strong[{typ_lit(m.group("b1") or m.group("b2"))}]')
        elif m.group('i1') is not None or m.group('i2') is not None:
            out.append(f'#emph[{typ_lit(m.group("i1") or m.group("i2"))}]')
        else:
            out.append(f'#raw({typ_str(m.group("code"))})')
        pos = m.end()
    if pos < len(s):
        out.append(typ_lit(s[pos:]))
    return ''.join(out)


def raw_typst_inline(code: str) -> str:
    """Wrap verbatim Typst ``code`` as a pandoc raw inline ( `...`{=typst} ).

    The fence is one backtick longer than the longest backtick run inside the
    payload, so literal backticks in added text can't close the span early.
    """
    longest = max((len(r) for r in re.findall(r'`+', code)), default=0)
    fence = '`' * (longest + 1)
    return f'{fence}{code}{fence}{{=typst}}'


def _wrap(s: str, fn):
    """Apply wrapper ``fn`` to the non-space core of ``s``, leaving surrounding
    whitespace outside (markdown strikeout and our red span both require the
    delimiters to hug non-space)."""
    if not s or s.strip() == '':
        return s
    m = re.match(r'^(\s*)(.*?)(\s*)$', s, re.S)
    lead, core, trail = m.group(1), m.group(2), m.group(3)
    return lead + fn(core) + trail


def wrap_strike(s: str) -> str:
    return _wrap(s, lambda core: f'~~{core}~~')


def wrap_red(s: str) -> str:
    return _wrap(s, lambda core: raw_typst_inline(f'{RED}[{md_inline_to_typ(core)}]'))


# --plain: the markdown redline that survives in the repository (the PDF does
# not -- releases/**/*.pdf is gitignored). Additions **bold**, deletions ~~struck~~
# (already markdown), and no Typst anywhere in the markup. Decision D1.
UNMARKED_FIGURE_NOTE = '<!-- unmarked: new or regenerated figure -->'
# The comment renders as nothing (pandoc, GitHub), so it travels with a visible
# line: a new or regenerated figure must not read as "compared and unchanged". The
# comment stays its own whole line -- is_unmarkable_structure keys on that. The
# visible line below is still used by the --full/digest path; --source writes the
# new/changed note of Wave 3b instead (NOTE_BLOCK_ADDED / NOTE_BLOCK_CHANGED).
UNMARKED_FIGURE_VISIBLE = '*[figure new or regenerated — shown unmarked]*'
# Structural notes (Wave 3b, ruling 1): italic, bracketed BODY paragraphs, never
# red (red means added Code text), never struck (strike means deleted Code text),
# never a heading (the integrated TOC is read back from the PDF). The same text in
# both modes. Labels come from structure_text and never carry a split-marker token.
NOTE_HEADING_REMOVED = '*[Heading removed: “{}”]*'
NOTE_HEADING_ADDED = '*[Heading added]*'
NOTE_HEADING_CHANGED = '*[Heading changed — it read: “{}”]*'
NOTE_TITLE_CHANGED = '*[Article title changed \u2014 it read: \u201c{}\u201d]*'
NOTE_BLOCK_REMOVED = '*[Table or figure removed: “{}”]*'
NOTE_BLOCK_ADDED = '*[New table or figure, shown in full: “{}”]*'
NOTE_BLOCK_CHANGED = ('*[Table or figure changed — shown in its current form, '
                      'not marked: “{}”]*')
_STRUCT = {'n': 0}


def _note(template: str, label: str = '') -> str:
    _STRUCT['n'] += 1
    for ch in '\\*_[]`@#':
        label = label.replace(ch, '\\' + ch)
    return template.format(label)


# Leading marker for a line added in its ENTIRETY. The Code bolds every defined
# term (548x in Article 9), so **bold** alone cannot tell an added term from an
# unchanged one. U+2295 renders as visible text through pandoc -f gfm, is not
# markdown structure (unlike a bare + or >), and appears nowhere in source/.
SIGIL = '\u2295'
LEGEND_KEY = ('Redline key: **bold** = text added; ~~struck~~ = text deleted; '
              f'{SIGIL} marks a line that is new in its entirety')
# Only the --full path still writes the visible "figure new or regenerated" line
# (UNMARKED_FIGURE_VISIBLE); --source writes the structural notes instead, so its
# legend must not define a phrase its output never contains.
LEGEND_FIGURE_CLAUSE = ('; "figure new or regenerated \u2014 shown unmarked" = a figure shown in its '
                        'current form, not compared.')
LEGEND = LEGEND_KEY + LEGEND_FIGURE_CLAUSE
# --source marks prose and table rows ONLY (headings and raw-Typst blocks are shown
# in their current form). A heading or block that was added, removed or changed
# leaves a note at that spot (Wave 3b): a removal no longer leaves no trace. The
# legend for that mode must not promise more, in either direction.
LEGEND_SOURCE_LIMITS = ('Only prose and the rows of simple tables are marked word by word. Headings, '
                        'figures and complex tables (those laid out as figures rather than as plain '
                        'rows) are shown in their current form; where one was added, removed or '
                        'changed, a note in italics and square brackets says so at that spot. '
                        'See the Summary of Changes for detail.')
PLAIN = False


def wrap_bold(s: str) -> str:
    return _wrap(s, lambda core: f'**{core}**')


def set_plain_mode() -> None:
    """Switch the redline markup from Typst spans to plain markdown.

    strike_line/red_line and strike_pipe/red_pipe resolve ``wrap_red`` as a
    module global at call time, so rebinding it reaches every caller without
    threading a flag through the dispatch. Deletions already use markdown
    ``~~`` -- only additions carried Typst. The few places that build Typst
    directly (the native-block note, the digest's breadcrumbs/rules/summary)
    consult ``PLAIN`` themselves.
    """
    global wrap_red, PLAIN
    PLAIN = True
    wrap_red = wrap_bold


def add_legend(result: str, source: bool = False) -> str:
    """Put the one-line convention legend at the head of plain output -- after the
    YAML front-matter when there is one, since --source output is a document the
    build reads and front-matter must stay first. ``source`` appends the limits
    of --source marking (see LEGEND_SOURCE_LIMITS)."""
    fm, body = split_frontmatter(result)
    legend = (LEGEND_KEY + '.' + ' ' + LEGEND_SOURCE_LIMITS) if source else LEGEND
    return fm + legend + '\n\n' + body.lstrip('\n')


# ---------------------------------------------------------------------------
# Prose lines
# ---------------------------------------------------------------------------

def split_prefix(line: str):
    m = PREFIX_RE.match(line)
    return m.group(1), m.group(2)


def tokenize(s: str):
    """Split into alternating word / whitespace tokens (whitespace preserved)."""
    return re.findall(r'\s+|\S+', s)


def token_diff(a_toks, b_toks) -> str:
    sm = difflib.SequenceMatcher(None, a_toks, b_toks, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        old = ''.join(a_toks[i1:i2])
        new = ''.join(b_toks[j1:j2])
        if tag == 'equal':
            out.append(old)
        elif tag == 'delete':
            out.append(wrap_strike(old))
        elif tag == 'insert':
            out.append(wrap_red(new))
        else:  # replace — struck old immediately followed by red new
            out.append(wrap_strike(old))
            out.append(wrap_red(new))
    return ''.join(out)


def line_word_diff(old: str, new: str) -> str:
    po, co = split_prefix(old)
    pn, cn = split_prefix(new)
    if po == pn:
        return po + token_diff(tokenize(co), tokenize(cn))
    # Block marker itself changed (heading level / list type): mark whole lines.
    return strike_line(old) + '\n' + red_line(new)


def strike_line(ln: str) -> str:
    prefix, content = split_prefix(ln)
    return ln if content.strip() == '' else prefix + wrap_strike(content)


def red_line(ln: str) -> str:
    prefix, content = split_prefix(ln)
    if content.strip() == '':
        return ln
    return prefix + (SIGIL + ' ' if PLAIN else '') + wrap_red(content)


# ---------------------------------------------------------------------------
# Pipe-table rows  (mark cells, keep | delimiters so the row stays a table row)
# ---------------------------------------------------------------------------

def is_pipe_row(s: str) -> bool:
    return re.match(r'^[ \t]*\|', s) is not None


def is_pipe_sep(s: str) -> bool:
    return bool(re.match(r'^[ \t]*\|[\s:\-|]+\|?[ \t]*$', s)) and '-' in s


def pipe_cells(s: str):
    core = s.strip()
    if core.startswith('|'):
        core = core[1:]
    if core.endswith('|'):
        core = core[:-1]
    return core.split('|')


def join_pipe(cells) -> str:
    return '| ' + ' | '.join(c.strip() for c in cells) + ' |'


def strike_pipe(ln: str) -> str:
    if is_pipe_sep(ln):
        return ln
    return join_pipe([wrap_strike(c.strip()) for c in pipe_cells(ln)])


def red_pipe(ln: str) -> str:
    if is_pipe_sep(ln):
        return ln
    cells = [wrap_red(c.strip()) for c in pipe_cells(ln)]
    if PLAIN:
        cells[0] = (SIGIL + ' ' + cells[0]).strip()
    return join_pipe(cells)


def pipe_word_diff(old: str, new: str) -> str:
    if is_pipe_sep(old) or is_pipe_sep(new):
        return new
    co, cn = pipe_cells(old), pipe_cells(new)
    if len(co) == len(cn):
        return join_pipe([token_diff(tokenize(a.strip()), tokenize(b.strip()))
                          for a, b in zip(co, cn)])
    return strike_pipe(old) + '\n' + red_pipe(new)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def emit_equal(ln: str, reg: dict) -> str:
    return reg[ln] if is_block_token(ln) else ln


def emit_deleted(ln: str, reg: dict) -> str:
    if is_block_token(ln):
        return wrap_strike('[native-Typst block removed — see rendered Code]')
    return strike_pipe(ln) if is_pipe_row(ln) else strike_line(ln)


def emit_inserted(ln: str, reg: dict) -> str:
    if is_block_token(ln):
        if PLAIN:
            return UNMARKED_FIGURE_NOTE + '\n\n' + UNMARKED_FIGURE_VISIBLE + '\n\n' + reg[ln] + '\n'
        note = wrap_red('[native-Typst block added or updated — current version rendered below]')
        return note + '\n\n' + reg[ln] + '\n'
    return red_pipe(ln) if is_pipe_row(ln) else red_line(ln)


def mark_replace_1to1(old: str, new: str) -> str:
    if is_pipe_row(old) and is_pipe_row(new):
        return pipe_word_diff(old, new)
    if not is_pipe_row(old) and not is_pipe_row(new):
        return line_word_diff(old, new)
    return emit_deleted(old, {}) + '\n' + emit_inserted(new, {})


def redline(old_text: str, new_text: str):
    a, reg_a = prepare(old_text)
    b, reg_b = prepare(new_text)
    reg = {**reg_a, **reg_b}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    n_del = n_ins = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out.extend(emit_equal(ln, reg) for ln in a[i1:i2])
        elif tag == 'delete':
            n_del += sum(1 for ln in a[i1:i2] if ln.strip())
            out.extend(emit_deleted(ln, reg) for ln in a[i1:i2])
        elif tag == 'insert':
            n_ins += sum(1 for ln in b[j1:j2] if ln.strip())
            out.extend(emit_inserted(ln, reg) for ln in b[j1:j2])
        else:  # replace
            n_del += sum(1 for ln in a[i1:i2] if ln.strip())
            n_ins += sum(1 for ln in b[j1:j2] if ln.strip())
            ol, nl = a[i1:i2], b[j1:j2]
            if (len(ol) == 1 and len(nl) == 1
                    and not is_block_token(ol[0]) and not is_block_token(nl[0])):
                out.append(mark_replace_1to1(ol[0], nl[0]))
            else:
                out.extend(emit_deleted(ln, reg) for ln in ol)
                out.extend(emit_inserted(ln, reg) for ln in nl)
    return '\n'.join(out), n_del, n_ins


# ---------------------------------------------------------------------------
# Changes-only digest  (default): only changed passages, each under its
# Section-heading breadcrumb with a few lines of context. Skips unchanged text.
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r'^(#{1,6})[ \t]+(.*?)[ \t]*$')
BLUE = '#367AAC'
GRAY = '#7C766F'
HAIR = '#BFBFBF'


def raw_typst_para(code: str) -> str:
    """A standalone paragraph that is one raw-Typst inline."""
    return raw_typst_inline(code)


def heading_index(lines):
    """(line_index, level, text) for every ATX heading in ``lines``."""
    out = []
    for idx, ln in enumerate(lines):
        m = HEADING_RE.match(ln)
        if m:
            out.append((idx, len(m.group(1)), m.group(2)))
    return out


def breadcrumb_at(headings, j):
    """Heading path (levels 1..3) in effect at NEW-doc line index ``j``."""
    path = {}
    for idx, level, text in headings:
        if idx > j:
            break
        if level <= 3:
            path = {k: v for k, v in path.items() if k < level}
            path[level] = text
    return [path[k] for k in sorted(path)]


def crumb_line(crumb) -> str:
    text = ' › '.join(crumb) if crumb else '(document start)'
    if PLAIN:
        return f'**{text}**'
    return raw_typst_para(f'#text(fill: rgb("{BLUE}"), weight: "bold", size: 11pt)[{typ_lit(text)}]')


def rule_line() -> str:
    if PLAIN:
        return '---'
    return raw_typst_para(f'#line(length: 100%, stroke: 0.5pt + rgb("{HAIR}"))')


def context_line(ln: str, reg: dict) -> str:
    """Unchanged orientation line. Whole native-Typst blocks are collapsed to a
    one-line placeholder so a digest hunk doesn't dump an entire table."""
    if is_block_token(ln):
        if PLAIN:
            return '*[unchanged table/figure omitted]*'
        return raw_typst_para(f'#text(fill: rgb("{GRAY}"), style: "italic")[\\[unchanged table/figure omitted\\]]')
    return ln


def _has_text(lines) -> bool:
    """True if any line carries non-whitespace content."""
    return any(ln.strip() for ln in lines)


def _changed_lines(group, a, b):
    """The old- and new-side lines touched by a hunk's non-equal opcodes."""
    old, new = [], []
    for tag, i1, i2, j1, j2 in group:
        if tag in ('delete', 'replace'):
            old.extend(a[i1:i2])
        if tag in ('insert', 'replace'):
            new.extend(b[j1:j2])
    return old, new


def digest(old_text: str, new_text: str, context: int = 2):
    a, reg_a = prepare(old_text)
    b, reg_b = prepare(new_text)
    reg = {**reg_a, **reg_b}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    b_headings = heading_index(b)
    out = []
    n_del = n_ins = n_hunks = 0
    for group in sm.get_grouped_opcodes(context):
        old_ch, new_ch = _changed_lines(group, a, b)
        # Skip hunks whose only difference is blank-line churn: a paragraph gap
        # opening or closing is not a textual change and must not flag a passage
        # (e.g. a removed HTML-comment placeholder that leaves a blank line).
        if not _has_text(old_ch) and not _has_text(new_ch):
            continue
        jstart = group[0][3]
        if n_hunks > 0:
            out.append('')
            out.append(rule_line())
        out.append('')
        out.append(crumb_line(breadcrumb_at(b_headings, jstart)))
        out.append('')
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                out.extend(context_line(ln, reg) for ln in b[j1:j2])
            elif tag == 'delete':
                n_del += sum(1 for ln in a[i1:i2] if ln.strip())
                out.extend(emit_deleted(ln, reg) for ln in a[i1:i2])
            elif tag == 'insert':
                n_ins += sum(1 for ln in b[j1:j2] if ln.strip())
                out.extend(emit_inserted(ln, reg) for ln in b[j1:j2])
            else:
                n_del += sum(1 for ln in a[i1:i2] if ln.strip())
                n_ins += sum(1 for ln in b[j1:j2] if ln.strip())
                ol, nl = a[i1:i2], b[j1:j2]
                if (len(ol) == 1 and len(nl) == 1
                        and not is_block_token(ol[0]) and not is_block_token(nl[0])):
                    out.append(mark_replace_1to1(ol[0], nl[0]))
                else:
                    out.extend(emit_deleted(ln, reg) for ln in ol)
                    out.extend(emit_inserted(ln, reg) for ln in nl)
        n_hunks += 1
    no_change = 'No textual changes between the two versions. (Layout, native tables, and images are not compared.)'
    passages = f'{n_hunks} changed passage(s) shown below, each under its Section location. Unchanged text is omitted.'
    if n_hunks == 0:
        body = (f'*{no_change}*' if PLAIN else
                raw_typst_para(f'#text(fill: rgb("{GRAY}"), style: "italic")[{no_change}]'))
    else:
        summary = (f'*{passages}*' if PLAIN else
                   raw_typst_para(f'#text(style: "italic")[{passages}]'))
        body = summary + '\n' + '\n'.join(out)
    return body, n_del, n_ins, n_hunks


# ---------------------------------------------------------------------------
# Source-file mode  (--source): redline ONE article .md in place, marking prose
# while keeping the file structurally intact for the integrated build. Unlike
# the concatenated-deliverable modes above it PRESERVES the YAML front-matter
# and the HTML splice markers, does NOT drop native ``## D..`` sections, emits
# fenced / raw-Typst blocks as the NEW version verbatim (no note), and leaves
# ATX heading lines as the NEW text unmarked — so the scanned TOC and the
# per-Article running heads stay clean. Figure/data and heading/section changes
# are narrated in the hand-written Summary instead.
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r'^---[ \t]*\n.*?\n---[ \t]*\n?', re.S)
HEADING_LINE_RE = re.compile(r'^\s*#{1,6}[ \t]')


def split_frontmatter(text: str):
    """Return ``(frontmatter_or_'', body)``, peeling a single leading
    ``---`` … ``---`` YAML block (the per-Article metadata the build chrome reads)."""
    m = FRONTMATTER_RE.match(text)
    return (m.group(0), text[m.end():]) if m else ('', text)


def prepare_source(text: str):
    """Mask fenced blocks only — keep front-matter (split off by the caller),
    HTML comments, and native ``## D..`` sections intact."""
    return mask_blocks(text)


def is_heading(ln: str) -> bool:
    return bool(HEADING_LINE_RE.match(ln))


HTML_COMMENT_LINE_RE = re.compile(r'^\s*<!--.*?-->\s*$', re.S)


def is_unmarkable_structure(ln: str) -> bool:
    """A line that is WHOLLY an HTML comment.

    These carry structure, not prose: build-standalone.sh and build-full-czc.sh
    seat native-Typst units at them (source/article-03-*.md's TYPE-PAGES and
    STREET-TYPE-EXHIBITS). prepare_source deliberately keeps HTML comments
    intact, so without this a DELETED marker is struck rather than dropped,
    reaching the marked file as ``~~<!-- TYPE-PAGES -->~~``. split-article-03.py
    matches markers by substring, so it then splits at a marker the new source
    does not have and exits 0 -- the plates are seated in a position the real
    document lacks. Measured 2026-10-07.

    Narrow by construction: a prose line that merely mentions the token, or that
    carries a trailing inline comment, is not wholly a comment and is still marked.

    Known limits: the match is per line, so a MULTI-line comment is not
    recognised; and the lazy ``.*?`` spans a middle, so ``<!-- a --> prose
    <!-- b -->`` is (wrongly) treated as structure. Neither occurs in source/*.md,
    where every structural comment is a single line.
    """
    return bool(HTML_COMMENT_LINE_RE.match(ln))


def _markable(ln: str) -> bool:
    """A line that actually receives a mark (used only for the stderr tally)."""
    return (bool(ln.strip()) and not is_block_token(ln) and not is_heading(ln)
            and not is_unmarkable_structure(ln))


_NO_CTX = {'removed': set(), 'added': set(), 'changed': set(),
           'h_removed': set(), 'h_added': set(), 'h_changed': {}}


def emit_deleted_src(ln: str, reg: dict, ctx: dict | None = None, pos: int = -1) -> str:
    ctx = ctx or _NO_CTX
    if is_block_token(ln):
        # A changed block's note sits at its new version; a moved one needs none.
        if ln not in ctx['removed']:
            return ''
        return _note(NOTE_BLOCK_REMOVED, structure_text.block_caption(reg[ln]))
    if is_heading(ln):
        # A changed heading's note sits at its new version; an unchanged one needs none.
        if pos not in ctx['h_removed']:
            return ''
        return _note(NOTE_HEADING_REMOVED, structure_text.heading_label(ln))
    if is_unmarkable_structure(ln):
        return ''            # build structure (a split marker), not Code text: silent (ruling 5)
    return strike_pipe(ln) if is_pipe_row(ln) else strike_line(ln)


def emit_inserted_src(ln: str, reg: dict, ctx: dict | None = None, pos: int = -1) -> str:
    ctx = ctx or _NO_CTX
    if is_block_token(ln):
        if ln in ctx['changed']:
            template = NOTE_BLOCK_CHANGED
        elif ln in ctx['added']:
            template = NOTE_BLOCK_ADDED
        else:
            return reg[ln]   # an unchanged block that only moved: no note
        note = _note(template, structure_text.block_caption(reg[ln]))
        lead = (UNMARKED_FIGURE_NOTE + '\n\n') if PLAIN else ''
        return lead + note + '\n\n' + reg[ln]
    if is_heading(ln):
        # the heading stays a heading (TOC, structure); the note is its own paragraph after it
        if pos in ctx['h_added']:
            return ln + '\n\n' + _note(NOTE_HEADING_ADDED)
        if pos in ctx['h_changed']:
            return ln + '\n\n' + _note(NOTE_HEADING_CHANGED, ctx['h_changed'][pos])
        return ln
    if is_unmarkable_structure(ln):
        return ln            # NEW split marker VERBATIM: it is structure the splitter reads
    return red_pipe(ln) if is_pipe_row(ln) else red_line(ln)


_TITLE_RE = re.compile(r'^article-name:[ \t]*(.*?)[ \t]*$', re.M)


def _article_title(fm: str):
    m = _TITLE_RE.search(fm)
    return m.group(1).strip('"\'') if m else None


def emit_equal_src(old_ln: str, new_ln: str, reg: dict, ctx: dict, i: int, j: int) -> str:
    """An unchanged line -- except that the text must reflect the heading
    classification fully, whatever the body diff did: a heading classified added
    or changed gets its note after it; one classified removed leaves its note."""
    if not is_heading(new_ln) and not is_heading(old_ln):
        return emit_equal(new_ln, reg)
    out = []
    if is_heading(old_ln) and i in ctx['h_removed']:
        out.append(_note(NOTE_HEADING_REMOVED, structure_text.heading_label(old_ln)))
    if is_heading(new_ln):
        if j in ctx['h_added']:
            out.append(new_ln + '\n\n' + _note(NOTE_HEADING_ADDED))
        elif j in ctx['h_changed']:
            out.append(new_ln + '\n\n' + _note(NOTE_HEADING_CHANGED, ctx['h_changed'][j]))
        else:
            out.append(new_ln)
    return '\n\n'.join(out)


def redline_source(old_text: str, new_text: str):
    """Mark prose in one article ``.md`` (OLD vs NEW) while preserving NEW
    front-matter and structure. Returns ``(marked_markdown, n_del, n_ins)``."""
    new_fm, new_body = split_frontmatter(new_text)
    old_fm, old_body = split_frontmatter(old_text)
    a, reg_a = prepare_source(old_body)
    b, reg_b = prepare_source(new_body)
    reg = {**reg_a, **reg_b}
    _STRUCT['n'] = 0
    # One classifier (structure_text.classify_blocks) decides added / removed /
    # changed for raw blocks -- the same one the disclosure page uses.
    a_heads = [k for k, t in enumerate(a) if is_heading(t)]
    b_heads = [k for k, t in enumerate(b) if is_heading(t)]
    hcls = structure_text.classify_headings([a[k] for k in a_heads], [b[k] for k in b_heads])
    old_toks = [t for t in a if is_block_token(t)]
    new_toks = [t for t in b if is_block_token(t)]
    cls = structure_text.classify_blocks([reg_a[t] for t in old_toks], [reg_b[t] for t in new_toks])
    ctx = {'removed': {old_toks[i] for i in cls['removed']},
           'added': {new_toks[j] for j in cls['added']},
           'changed': {new_toks[j] for _, j in cls['changed']},
           'h_removed': {a_heads[i] for i in hcls['removed']},
           'h_added': {b_heads[j] for j in hcls['added']},
           'h_changed': {b_heads[j]: structure_text.heading_label(a[a_heads[i]])
                         for i, j in hcls['changed']}}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    n_del = n_ins = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out.extend(emit_equal_src(ln, b[j1 + k], reg, ctx, i1 + k, j1 + k)
                       for k, ln in enumerate(a[i1:i2]))
        elif tag == 'delete':
            n_del += sum(1 for ln in a[i1:i2] if _markable(ln))
            out.extend(emit_deleted_src(ln, reg, ctx, i1 + k) for k, ln in enumerate(a[i1:i2]))
        elif tag == 'insert':
            n_ins += sum(1 for ln in b[j1:j2] if _markable(ln))
            out.extend(emit_inserted_src(ln, reg, ctx, j1 + k) for k, ln in enumerate(b[j1:j2]))
        else:  # replace
            ol, nl = a[i1:i2], b[j1:j2]
            n_del += sum(1 for ln in ol if _markable(ln))
            n_ins += sum(1 for ln in nl if _markable(ln))
            if (len(ol) == 1 and len(nl) == 1
                    and not is_block_token(ol[0]) and not is_block_token(nl[0])
                    and not is_heading(ol[0]) and not is_heading(nl[0])
                    and not is_unmarkable_structure(ol[0])
                    and not is_unmarkable_structure(nl[0])):
                out.append(mark_replace_1to1(ol[0], nl[0]))
            else:
                out.extend(emit_deleted_src(ln, reg, ctx, i1 + k) for k, ln in enumerate(ol))
                out.extend(emit_inserted_src(ln, reg, ctx, j1 + k) for k, ln in enumerate(nl))
    body_marked = '\n'.join(out)
    old_title, new_title = _article_title(old_fm), _article_title(new_fm)
    if old_title is not None and new_title is not None and old_title != new_title:
        # the title is frontmatter, so no heading note can carry it: say it first
        body_marked = (_note(NOTE_TITLE_CHANGED, structure_text._clean(old_title))
                       + '\n\n' + body_marked)
    return ((new_fm + body_marked) if new_fm else body_marked), n_del, n_ins


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    if len(args) != 3:
        sys.exit('usage: redline-text.py <old.md> <new.md> <out.md> [--digest|--full|--source] [--plain]')
    old_f, new_f, out_f = args
    if '--plain' in flags:
        set_plain_mode()
    with open(old_f, encoding='utf-8') as f:
        old_text = f.read()
    with open(new_f, encoding='utf-8') as f:
        new_text = f.read()
    if '--full' in flags:
        result, n_del, n_ins = redline(old_text, new_text)
        n_hunks = None
    elif '--source' in flags:
        result, n_del, n_ins = redline_source(old_text, new_text)
        n_hunks = None
    else:  # default: changes-only digest
        result, n_del, n_ins, n_hunks = digest(old_text, new_text)
    if PLAIN:
        result = add_legend(result, source='--source' in flags)
    with open(out_f, 'w', encoding='utf-8') as f:
        f.write(result)
    extra = '' if n_hunks is None else f', {n_hunks} passage(s)'
    if '--source' in flags:
        extra = f', {_STRUCT["n"]} structural change(s) noted'
    print(f'redline: {n_del} line(s) removed, {n_ins} line(s) added{extra}', file=sys.stderr)


if __name__ == '__main__':
    main()
