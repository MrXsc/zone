"""Balanced left/right tree layout.

Strategy
--------
The root sits in the center. Its children are split into two groups: the
first half expand to the LEFT, the rest to the RIGHT, so the canvas
stays balanced and wide trees don't all lean one way. Subtrees beneath
each child keep expanding in their inherited direction.

Algorithm (classic two-pass tidier layout):
1. ``measure``  (post-order): compute each subtree's total height and the
   node's width from its text. A leaf's height is one node; a parent's is
   the sum of its children's heights plus sibling gaps.
2. ``place``    (pre-order):   assign coordinates. Within each subtree the
   parent is vertically centered on its children, and children stack top
   to bottom. Horizontal offset grows by ``level_gap`` per depth.

Direction is encoded as +1 (right) or -1 (left); x grows outward from
the parent in that direction. One code path serves both sides.

A final normalization shifts every box so min x and min y are 0,
removing negative coordinates produced by the left side.
"""

from __future__ import annotations

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.layout.contract import Box, LayoutOptions, LayoutResult

_RIGHT = 1   # children placed to the right of the parent's right edge
_LEFT = -1   # children placed to the left  of the parent's left  edge


def layout(mindmap: MindMap, options: LayoutOptions | None = None) -> LayoutResult:
    """Lay out ``mindmap`` as a balanced left/right tree.

    Returns a dict mapping node id -> Box with non-negative coordinates.
    """
    opts = options or LayoutOptions()
    boxes: LayoutResult = {}

    # --- Pass 1: measure heights and widths ----------------------------------
    heights: dict[str, float] = {}
    _measure(mindmap.root, opts, heights, boxes)

    # --- Pass 2: place coordinates -------------------------------------------
    # Root sits at the origin. Its own box is vertically centered on the
    # full tree height (its own subtree height = total canvas height).
    root = mindmap.root
    root_box = boxes[root.id]
    root_total_h = heights[root.id]
    boxes[root.id] = Box(x=0.0, y=(root_total_h - opts.node_height) / 2,
                         width=root_box.width, height=opts.node_height)

    if root.children:
        _place_children(root, direction_hint="root", opts=opts,
                        heights=heights, boxes=boxes)

    # --- Pass 3: normalize so min coords are 0 -------------------------------
    _normalize(boxes)
    return boxes


def _measure(node: Node, opts: LayoutOptions,
             heights: dict[str, float], boxes: LayoutResult) -> float:
    """Post-order: fill heights[id] and a placeholder box (width only)."""
    if node.is_leaf:
        h = opts.node_height
    else:
        kids_h = sum(_measure(c, opts, heights, boxes) for c in node.children)
        gaps = opts.sibling_gap * max(0, len(node.children) - 1)
        h = max(opts.node_height, kids_h + gaps)
    heights[node.id] = h

    width = max(opts.min_node_width,
                len(node.text) * opts.char_width + opts.h_padding * 2)
    # Placeholder; real x/y assigned during placement. Width/height are
    # final here so sizing is available even if placement is skipped.
    boxes[node.id] = Box(x=0.0, y=0.0, width=width, height=opts.node_height)
    return h


def _place_children(parent: Node, *, direction_hint: int | str,
                    opts: LayoutOptions, heights: dict[str, float],
                    boxes: LayoutResult) -> None:
    """Place ``parent``'s children and recurse into each.

    ``direction_hint`` is either ``"root"`` (split children left/right) or
    an inherited +/-1 direction. Children stack vertically, centered on
    the parent's vertical center, and step outward by ``level_gap``.
    """
    children = parent.children
    parent_box = boxes[parent.id]

    if direction_hint == "root":
        # Split: first floor(n/2) go LEFT, the rest go RIGHT.
        n = len(children)
        split = n // 2
        left_group = children[:split]
        right_group = children[split:]
        for group, direction in ((left_group, _LEFT), (right_group, _RIGHT)):
            if not group:
                continue
            _stack_and_recurse(group, parent_box, direction,
                               opts=opts, heights=heights, boxes=boxes)
    else:
        _stack_and_recurse(children, parent_box, direction_hint,
                           opts=opts, heights=heights, boxes=boxes)


def _stack_and_recurse(group: list[Node], parent_box: Box, direction: int,
                       *, opts: LayoutOptions, heights: dict[str, float],
                       boxes: LayoutResult) -> None:
    """Stack ``group`` vertically around the parent's center, then recurse."""
    total_h = sum(heights[c.id] for c in group)
    gaps = opts.sibling_gap * (len(group) - 1)
    block_h = total_h + gaps
    # Top of the block: center the block on the parent's vertical center.
    cursor_y = parent_box.cy - block_h / 2

    for child in group:
        child_h = heights[child.id]
        child_y = cursor_y + (child_h - opts.node_height) / 2
        child_w = boxes[child.id].width

        if direction == _RIGHT:
            child_x = parent_box.x + parent_box.width + opts.level_gap
        else:
            child_x = parent_box.x - opts.level_gap - child_w

        boxes[child.id] = Box(x=child_x, y=child_y, width=child_w,
                              height=opts.node_height)
        if not child.is_leaf:
            _place_children(child, direction_hint=direction, opts=opts,
                            heights=heights, boxes=boxes)
        cursor_y += child_h + opts.sibling_gap


def _normalize(boxes: LayoutResult) -> None:
    """Shift all boxes so min x and min y are 0."""
    if not boxes:
        return
    min_x = min(b.x for b in boxes.values())
    min_y = min(b.y for b in boxes.values())
    for nid, b in boxes.items():
        boxes[nid] = Box(x=b.x - min_x, y=b.y - min_y,
                         width=b.width, height=b.height)
