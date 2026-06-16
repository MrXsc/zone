"""SVG renderer — produce a self-contained .svg document.

Visual choices for the skeleton are deliberately restrained: a neutral
ink color, a single accent for the root, thin connectors, rounded boxes.
Per-node styling (color/font/weight) is out of scope by design and will
arrive behind a separate style interface.

Connector shape: a cubic Bezier from the parent's edge midpoint to the
child's edge midpoint, with horizontal control points so the curve
enters/leaves each node smoothly. This is the classic mind-map curve.

We build the document from plain strings — no template engine, no XML
library — keeping the zero-dependency promise. Output is XML-escaped via
the stdlib so text never breaks the markup.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.layout.contract import Box, LayoutResult

# --- palette (skeleton defaults; not user-tunable yet) --------------------- #
_BG = "#fafafa"
_INK = "#1f2933"
_SUBTLE = "#9aa5b1"
_ROOT_FILL = "#1f2933"
_ROOT_TEXT = "#ffffff"
_NODE_FILL = "#ffffff"
_NODE_STROKE = "#c3cad2"
_CONNECTOR = "#9aa5b1"

_STROKE = 1.2
_ROOT_RX = 8.0
_NODE_RX = 6.0
_FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, " \
               "'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
_FONT_SIZE = 14
_PADDING = 24.0  # canvas padding around content


def render_svg(mindmap: MindMap, boxes: LayoutResult) -> str:
    """Render ``mindmap`` with the given layout to an SVG string."""
    if not boxes:
        # Degenerate: nothing to draw; emit a minimal valid SVG.
        return _document(0, 0, _PADDING, "")

    width, height = _bounds(boxes)
    body_parts: list[str] = [_styles()]
    # Connectors first so nodes paint over them.
    body_parts.append(_connectors(mindmap.root, boxes))
    body_parts.append(_nodes(mindmap, boxes))
    body = "\n".join(body_parts)
    return _document(width, height, _PADDING, body)


# --------------------------------------------------------------------------- #
#  geometry helpers
# --------------------------------------------------------------------------- #

def _bounds(boxes: LayoutResult) -> tuple[float, float]:
    """Return (content_width, content_height) of the laid-out boxes."""
    max_x = max(b.x + b.width for b in boxes.values())
    max_y = max(b.y + b.height for b in boxes.values())
    return max_x, max_y


def _document(width: float, height: float, pad: float, body: str) -> str:
    """Wrap ``body`` in a sized <svg> document with background."""
    w = width + pad * 2
    h = height + pad * 2
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}">\n'
        f'  <rect x="0" y="0" width="{w:g}" height="{h:g}" fill="{_BG}"/>\n'
        f'  <g transform="translate({_PADDING:g}, {_PADDING:g})">\n'
        f'{body}\n'
        f'  </g>\n'
        f'</svg>\n'
    )


def _styles() -> str:
    return (
        "  <style>\n"
        f"    .mm-text {{ fill: {_INK}; font-family: {_FONT_FAMILY}; "
        f"font-size: {_FONT_SIZE}px; }}\n"
        f"    .mm-root-text {{ fill: {_ROOT_TEXT}; font-family: {_FONT_FAMILY}; "
        f"font-size: {_FONT_SIZE}px; font-weight: 600; }}\n"
        "  </style>"
    )


def _nodes(mindmap: MindMap, boxes: LayoutResult) -> str:
    parts: list[str] = []
    for node in mindmap.walk():
        if node.id not in boxes:
            continue
        parts.append(_node_shape(node, boxes[node.id],
                                 is_root=(node is mindmap.root)))
    return "\n".join(parts)


def _node_shape(node: Node, box: Box, *, is_root: bool) -> str:
    fill = _ROOT_FILL if is_root else _NODE_FILL
    stroke = "none" if is_root else _NODE_STROKE
    rx = _ROOT_RX if is_root else _NODE_RX
    cls = "mm-root-text" if is_root else "mm-text"
    # Vertically center text: box.cy + ~0.35 * font-size (baseline trick).
    text_y = box.cy + _FONT_SIZE * 0.35
    label = escape(node.text) or " "
    return (
        f'    <rect x="{box.x:g}" y="{box.y:g}" width="{box.width:g}" '
        f'height="{box.height:g}" rx="{rx:g}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{_STROKE:g}"/>\n'
        f'    <text class="{cls}" x="{box.cx:g}" y="{text_y:g}" '
        f'text-anchor="middle">{label}</text>'
    )


def _connectors(root: Node, boxes: LayoutResult) -> str:
    """Emit a Bezier curve for every parent->child edge."""
    parts: list[str] = []
    for parent in root.walk():
        if parent.is_leaf or parent.id not in boxes:
            continue
        pbox = boxes[parent.id]
        for child in parent.children:
            if child.id not in boxes:
                continue
            parts.append(_connector(pbox, boxes[child.id]))
    return "\n".join(parts)


def _connector(parent: Box, child: Box) -> str:
    """Cubic Bezier from the parent edge to the child edge.

    Control points sit horizontally offset from the endpoints so the curve
    flows out of the parent and into the child horizontally — the classic
    mind-map sweep. Direction is inferred from which side the child is on.
    """
    if child.cx >= parent.cx:
        # Child is to the right: leave parent's right edge, enter child's left.
        x0, y0 = parent.x + parent.width, parent.cy
        x1, y1 = child.x, child.cy
        dx = (x1 - x0) * 0.5
    else:
        # Child is to the left: mirror.
        x0, y0 = parent.x, parent.cy
        x1, y1 = child.x + child.width, child.cy
        dx = (x1 - x0) * 0.5
    cx0, cy0 = x0 + dx, y0
    cx1, cy1 = x1 - dx, y1
    return (
        f'    <path d="M {x0:g} {y0:g} C {cx0:g} {cy0:g}, '
        f'{cx1:g} {cy1:g}, {x1:g} {y1:g}" '
        f'fill="none" stroke="{_CONNECTOR}" stroke-width="{_STROKE:g}"/>'
    )
