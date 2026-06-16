"""Bidirectional MindMap <-> Markdown conversion.

Grammar (the simplest thing that could work):

    # Document Title               <- optional; becomes MindMap.title

    - root topic                   <- exactly one top-level item = root
        - branch one
            - leaf
        - branch two

Each level of nesting is two spaces relative to its parent. Both 2-space
and 4-space indentation are tolerated on import (we infer depth from
leading whitespace, not a fixed step). Tabs are converted to spaces.

Lossiness: importing Markdown regenerates ids and drops notes. Exporting
keeps text and structure faithfully.
"""

from __future__ import annotations

import re

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node

# A list item looks like:  <indent>- <text>
# We capture indent (leading whitespace) and the text after the marker.
_ITEM_RE = re.compile(r"^(?P<indent>\s*)[-*+]\s+(?P<text>.*\S)\s*$")
# A heading:  # Title  (1-6 leading '#')
_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<title>.*\S)\s*$")

# Indent unit used on export. Two spaces is the Markdown convention and
# renders cleanly in any editor / preview.
_EXPORT_INDENT = "  "


# --------------------------------------------------------------------------- #
#  MindMap -> Markdown
# --------------------------------------------------------------------------- #

def to_markdown(mindmap: MindMap) -> str:
    """Render a MindMap as a Markdown indented list.

    Layout: an optional ``# title`` heading, a blank line, then the tree
    as nested bullets rooted at the root node.
    """
    lines: list[str] = []
    if mindmap.title:
        lines.append(f"# {mindmap.title}")
        lines.append("")  # blank line separates heading from list
    _emit_node(lines, mindmap.root, depth=0)
    # Trailing newline for POSIX-friendliness.
    return "\n".join(lines).rstrip("\n") + "\n"


def _emit_node(lines: list[str], node: Node, depth: int) -> None:
    """Append ``node`` and its subtree at the given nesting depth."""
    indent = _EXPORT_INDENT * depth
    # text may be empty; still emit a bullet so structure is visible.
    lines.append(f"{indent}- {node.text}")
    for child in node.children:
        _emit_node(lines, child, depth + 1)


# --------------------------------------------------------------------------- #
#  Markdown -> MindMap
# --------------------------------------------------------------------------- #

def from_markdown(text: str, *, title: str | None = None) -> MindMap:
    """Parse Markdown text into a MindMap.

    ``title``: if provided, overrides any heading-derived title.

    Raises ValueError if no top-level list item is found (no root), or if
    more than one is found (ambiguous root).
    """
    heading, items = _scan(text)

    if title is None:
        title = heading or "Untitled"

    if not items:
        raise ValueError("No root node found: expected at least one list item")

    # Roots are depth-0 items. Exactly one is required for a tree.
    roots = [it for it in items if it.depth == 0]
    if len(roots) != 1:
        raise ValueError(
            f"Expected exactly one top-level list item (the root), "
            f"found {len(roots)}"
        )

    root = _build_tree(items)
    return MindMap(title=title, root=root)


# --------------------------------------------------------------------------- #
#  Parsing internals
# --------------------------------------------------------------------------- #

class _Item:
    """A parsed list item: its text and indentation depth (in steps)."""

    __slots__ = ("text", "depth")

    def __init__(self, text: str, depth: int) -> None:
        self.text = text
        self.depth = depth


def _scan(text: str) -> tuple[str | None, list[_Item]]:
    """Tokenize text into (heading, [items]).

    Depth is computed by clustering observed indents: we collect every
    distinct leading-whitespace length among list items, sort them, and
    map each to a rank. This tolerates 2-space, 4-space, or mixed steps.
    Blank lines and non-list, non-heading lines are ignored (so prose
    between nodes doesn't break parsing).
    """
    heading: str | None = None
    raw: list[tuple[int, str]] = []  # (indent_width, text)

    for line in text.splitlines():
        if not line.strip():
            continue  # blank line

        m = _HEADING_RE.match(line)
        if m and heading is None:
            # First heading becomes the title; further headings are ignored
            # (kept simple: a heading after the list is unusual).
            heading = m.group("title")
            continue

        m = _ITEM_RE.match(line)
        if m:
            indent = m.group("indent").expandtabs(2)
            raw.append((len(indent), m.group("text")))
            continue
        # Non-matching line: ignore (tolerant parsing).

    if not raw:
        return heading, []

    # Map distinct indent widths -> depth ranks (0, 1, 2, ...).
    widths = sorted({w for w, _ in raw})
    width_to_depth = {w: i for i, w in enumerate(widths)}

    items = [_Item(text=t, depth=width_to_depth[w]) for w, t in raw]
    return heading, items


def _build_tree(items: list[_Item]) -> Node:
    """Reconstruct the Node tree from a flat, depth-tagged item list.

    Uses an explicit stack: each entry is (node, its_depth). For each new
    item we pop until the stack top is shallower than the item, then attach
    the new node as a child of the new stack top. The first item is root.
    """
    root = Node.create(items[0].text)
    stack: list[tuple[Node, int]] = [(root, items[0].depth)]

    for item in items[1:]:
        node = Node.create(item.text)
        # Pop until the stack top is the intended parent (shallower depth).
        while stack and stack[-1][1] >= item.depth:
            stack.pop()
        if not stack:
            # Depth jumped above the root — shouldn't happen given roots==1,
            # but guard anyway: treat as a child of root.
            root.add_child(node)
            stack = [(node, item.depth)]
            continue
        stack[-1][0].add_child(node)
        stack.append((node, item.depth))

    return root
