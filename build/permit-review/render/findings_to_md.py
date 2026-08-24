"""Render a node list to the markdown that render/build-findings.sh compiles.

Implements the render half of the permit-review render pipeline: engine/ and
llm/ (later workflows) will eventually assemble a list of small, typed nodes
describing one Findings of Fact & Conclusions of Law draft; this module's job
is only to turn that list into markdown bytes pandoc can hand to
style/findings-template.typ. It has no knowledge of the Code, the database, or
any particular case — it is a pure, dependency-free formatter.

THE MECHANISM (read this before changing anything below). pandoc's Typst
writer drops fenced-Div (`::: {.class}`) class names on the floor:

    $ printf '::: {.standard}\\nHello\\n:::\\n' | pandoc -f markdown+raw_attribute -t typst
    #block[
    Hello
    ]

The `.standard` class never reaches the output — there is no way for
style/findings-template.typ to key a `#show` rule off it, because by the time
Typst sees the document the class is simply gone. (Verified empirically
against the pandoc/typst versions this repo uses; re-check with the snippet
above if either is ever upgraded.)

The mechanism that DOES survive is the `raw_attribute` pandoc extension —
already enabled in both build/build-memo.sh's and this project's --from list,
and already the working pattern behind style/redline-template.typ (see its
header comment: "insertions arrive as raw Typst #text(fill: red)[...]"). A
fenced code block tagged `{=typst}` passes through byte-for-byte:

    $ printf '```{=typst}\\n#standard[Hello]\\n```\\n' | pandoc -f markdown+raw_attribute -t typst
    #standard[Hello]

So every node type below that needs one of the template's named helpers
(#standard, #finding, #unresolved, #boardq, #motionblock, #conditions,
#signaturegrid, #provenance) is emitted as a `{=typst}` raw block calling that
helper directly. Plain prose, headings and label/value tables are emitted as
ordinary markdown instead, since pandoc's own markdown -> Typst conversion
already handles those correctly and there is no reason to hand-roll them.

NODE SCHEMA. A node is a small dict with a "type" key:

    {"type": "heading", "level": 1-4, "text": str}
    {"type": "para", "text": str}                       # plain markdown prose
    {"type": "kv", "items": [(label, value), ...]}       # label/value block
    {"type": "table", "header": [str, ...], "rows": [[str, ...], ...]}
    {"type": "standard", "text": str, "citation": str | None}
    {"type": "finding", "text": str}
    {"type": "unresolved", "text": str}
    {"type": "boardq", "text": str}
    {"type": "motionblock", "motion": str | None, "moved_by": str | None,
     "second": str | None, "discussion": str | None, "yea": str | None,
     "nay": str | None, "abstain": str | None, "result": str | None}
    {"type": "conditions", "items": [str, ...]}          # [] renders one blank slot
    {"type": "signaturegrid", "members": [str | {"name": str, "title": str}, ...]}
    {"type": "rule"}                                     # horizontal divider
    {"type": "raw", "typst": str}                         # escape hatch

CONTRACT.md §5.1 note: a "citation" value on a node is always a string a
caller already produced (in the real app, via app/citation.py:render() — this
module never renders or invents citation text itself, it only prints
whatever string it is given).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

Node = Mapping[str, Any]

# --------------------------------------------------------------------------- #
# Escaping
# --------------------------------------------------------------------------- #

# Characters with syntactic meaning in Typst markup mode. Order matters:
# backslash must be escaped first, or the escapes added for every other
# character would themselves get re-escaped.
_TYPST_SPECIAL = "\\#[]<>@_*$`~"


def typst_escape(text: str) -> str:
    """Escape text for safe interpolation inside a raw ```{=typst}``` block.

    Any node text that ends up inside a #standard[...]/#finding[...]/etc. call
    is Typst *markup*, not a Python string literal — an unescaped `#`, `[`,
    `_`, `*` etc. in ordinance text or a name would be parsed as Typst syntax
    and could break the build or silently change how the text renders. This
    is the one thing every helper-emitting node below must run its text
    through.
    """
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch in _TYPST_SPECIAL:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append(" \\\n")  # Typst hard line break inside markup
        else:
            out.append(ch)
    return "".join(out)


# Markdown-significant characters, for the plain-prose path (headings, kv
# values, table cells) that pandoc parses as ordinary markdown rather than
# raw Typst. Real applicant/owner names and addresses can incidentally
# contain these (e.g. "M&T Bank", "Smith * Sons").
_MD_SPECIAL = "\\`*_{}[]()#+-.!|<>"


def md_escape(text: str) -> str:
    """Escape text that will be parsed as ordinary pandoc markdown."""
    out = []
    for ch in text:
        if ch in _MD_SPECIAL:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _typst_content(text: str) -> str:
    """Wrap escaped text as Typst content in square brackets."""
    return "[" + typst_escape(text) + "]"


def _typst_str_arg(value: str | None) -> str:
    """Render an optional string as a Typst string literal, or `none`."""
    if value is None or value == "":
        return "none"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _raw_block(typst_code: str) -> str:
    """Wrap literal Typst source in a raw_attribute fenced code block."""
    return "```{=typst}\n" + typst_code.rstrip("\n") + "\n```\n"


# --------------------------------------------------------------------------- #
# Per-node-type renderers
# --------------------------------------------------------------------------- #


def _render_heading(node: Node) -> str:
    level = int(node.get("level", 2))
    level = min(max(level, 1), 4)
    text = md_escape(str(node["text"]))
    return f"{'#' * level} {text}\n"


def _render_para(node: Node) -> str:
    return f"{node['text']}\n"


def _render_kv(node: Node) -> str:
    lines = []
    for label, value in node["items"]:
        label_md = md_escape(str(label))
        value_md = md_escape(str(value)) if value is not None else ""
        lines.append(f"**{label_md}:** {value_md}  ")  # trailing 2 spaces -> <br>
    return "\n".join(lines) + "\n"


def _render_table(node: Node) -> str:
    header: Sequence[str] = node["header"]
    rows: Sequence[Sequence[str]] = node.get("rows", [])
    out = ["| " + " | ".join(md_escape(str(h)) for h in header) + " |"]
    out.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows:
        out.append("| " + " | ".join(md_escape(str(c)) for c in row) + " |")
    return "\n".join(out) + "\n"


def _render_standard(node: Node) -> str:
    body = typst_escape(str(node["text"]))
    label = node.get("label")
    # Inline, with a small fixed skip -- NOT a fixed-width box. A box would
    # push the first line's text to margin+27; the real decisions start the
    # letter AND the standard's opening words together at margin+9, and hang
    # only the wrapped lines at +27.
    lead = f"{typst_escape(str(label))}#h(6pt)" if label else ""
    citation = node.get("citation")
    call = f"#standard[{lead}{body}"
    if citation:
        call += f"#provenance({_typst_str_arg(citation)})"
    call += "]"
    return _raw_block(call)


def _render_finding(node: Node) -> str:
    return _raw_block(f"#finding[{typst_escape(str(node['text']))}]")


def _render_unresolved(node: Node) -> str:
    return _raw_block(f"#unresolved[{typst_escape(str(node['text']))}]")


def _render_boardq(node: Node) -> str:
    return _raw_block(f"#boardq[{typst_escape(str(node['text']))}]")


_MOTIONBLOCK_FIELDS = (
    "motion", "moved_by", "second", "discussion", "yea", "nay", "abstain", "result",
)
_MOTIONBLOCK_TYPST_NAMES = {
    "moved_by": "moved-by",  # Python identifiers can't have hyphens; Typst's can
}


def _render_motionblock(node: Node) -> str:
    args = []
    for field in _MOTIONBLOCK_FIELDS:
        typst_name = _MOTIONBLOCK_TYPST_NAMES.get(field, field)
        value = node.get(field)
        args.append(f"{typst_name}: {_typst_str_arg(value)}")
    return _raw_block("#motionblock(\n  " + ",\n  ".join(args) + ",\n)")


def _render_conditions(node: Node) -> str:
    items = node.get("items", [])
    if not items:
        return _raw_block("#conditions(())")
    entries = ",\n  ".join(_typst_content(str(item)) for item in items)
    return _raw_block("#conditions((\n  " + entries + ",\n))")


def _member_to_typst(member: str | Mapping[str, Any]) -> str:
    if isinstance(member, Mapping):
        name = typst_escape(str(member.get("name", "")))
        title = member.get("title")
        title_part = f', title: "{typst_escape(str(title))}"' if title else ""
        return f'(name: "{name}"{title_part})'
    return _typst_str_arg(str(member))


def _render_signaturegrid(node: Node) -> str:
    members = node.get("members", [])
    entries = ",\n  ".join(_member_to_typst(m) for m in members)
    body = "#signaturegrid((\n  " + entries + ("," if entries else "") + "\n))"
    return _raw_block(body)


def _render_rule(node: Node) -> str:
    return "\n---\n"


def _render_raw(node: Node) -> str:
    return _raw_block(str(node["typst"]))


_RENDERERS = {
    "heading": _render_heading,
    "para": _render_para,
    "kv": _render_kv,
    "table": _render_table,
    "standard": _render_standard,
    "finding": _render_finding,
    "unresolved": _render_unresolved,
    "boardq": _render_boardq,
    "motionblock": _render_motionblock,
    "conditions": _render_conditions,
    "signaturegrid": _render_signaturegrid,
    "rule": _render_rule,
    "raw": _render_raw,
}


def node_to_md(node: Node) -> str:
    """Render a single node to a markdown fragment."""
    try:
        renderer = _RENDERERS[node["type"]]
    except KeyError as exc:
        raise ValueError(f"unknown node type: {node.get('type')!r}") from exc
    return renderer(node)


def render_nodes(nodes: Iterable[Node]) -> str:
    """Render an ordered list of nodes to a complete markdown document."""
    parts = [node_to_md(node) for node in nodes]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# Small convenience builders — optional sugar for callers assembling a node
# list by hand (engine/ will likely build node dicts directly instead, but
# these keep this module's own demo/tests readable).
# --------------------------------------------------------------------------- #


def heading(text: str, level: int = 2) -> dict:
    return {"type": "heading", "level": level, "text": text}


def para(text: str) -> dict:
    return {"type": "para", "text": text}


def kv(items: Sequence[tuple[str, Any]]) -> dict:
    return {"type": "kv", "items": list(items)}


def table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> dict:
    return {"type": "table", "header": list(header), "rows": [list(r) for r in rows]}


def standard(text: str, citation: str | None = None, label: str | None = None) -> dict:
    """`label` is the criterion letter ("d.") set in a FIXED-WIDTH BOX so it
    cannot break away from the standard's opening words. Measured from the real
    decisions: letter at margin+9pt, standard text and its wraps at margin+27pt.
    An em space here does NOT work -- Typst treats it as a break opportunity, so
    the letter lands on its own line and the hanging indent inverts."""
    return {"type": "standard", "text": text, "citation": citation, "label": label}


def finding(text: str) -> dict:
    return {"type": "finding", "text": text}


def unresolved(text: str) -> dict:
    return {"type": "unresolved", "text": text}


def boardq(text: str) -> dict:
    return {"type": "boardq", "text": text}


def motionblock(**fields: str | None) -> dict:
    unknown = set(fields) - set(_MOTIONBLOCK_FIELDS)
    if unknown:
        raise ValueError(f"unknown motionblock field(s): {sorted(unknown)}")
    return {"type": "motionblock", **fields}


def conditions(items: Sequence[str] = ()) -> dict:
    return {"type": "conditions", "items": list(items)}


def signaturegrid(members: Sequence[str | Mapping[str, Any]]) -> dict:
    return {"type": "signaturegrid", "members": list(members)}


def rule() -> dict:
    return {"type": "rule"}


def raw(typst_code: str) -> dict:
    return {"type": "raw", "typst": typst_code}


if __name__ == "__main__":
    import sys

    print(
        "findings_to_md.py is a library — import render_nodes(nodes) rather than "
        "running it directly. See build/permit-review/render/demo_findings.py "
        "for an end-to-end example.",
        file=sys.stderr,
    )
    sys.exit(1)
