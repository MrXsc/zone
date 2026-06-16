"""SVG renderer — produce a self-contained .svg document.

Visual choices are driven by a :class:`~mindmap.rendering.theme.Theme`
(defaults) plus an optional per-node :class:`~mindmap.domain.style.StyleMap`
overlay.  Passing no theme and no style map yields the same output as
before the M4 refactoring (backward-compatible).

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
from mindmap.domain.style import StyleMap
from mindmap.layout.contract import Box, LayoutResult
from mindmap.rendering.theme import DEFAULT_THEME, Theme, resolve


def render_svg(mindmap: MindMap, boxes: LayoutResult, *,
               theme: Theme = DEFAULT_THEME,
               style_map: StyleMap | None = None) -> str:
    """Render ``mindmap`` with the given layout to an SVG string.

    Args:
        mindmap:  The mind map to render.
        boxes:    Layout result from :func:`~mindmap.layout.layout`.
        theme:    Visual palette (defaults to a clean light theme).
        style_map:
            Optional per-node overrides.  ``None`` or empty = no overrides
            — every node uses *theme* values, matching the pre-M4 output.
    """
    if not boxes:
        # Degenerate: nothing to draw; emit a minimal valid SVG.
        return _document(0, 0, theme.padding, theme, "")

    width, height = _bounds(boxes)
    body_parts: list[str] = [_styles(theme)]
    # Connectors first so nodes paint over them.
    body_parts.append(_connectors(mindmap.root, boxes, theme=theme))
    body_parts.append(_nodes(mindmap, boxes, theme=theme, style_map=style_map))
    body = "\n".join(body_parts)
    return _document(width, height, theme.padding, theme, body)


# --------------------------------------------------------------------------- #
#  geometry helpers
# --------------------------------------------------------------------------- #

def _bounds(boxes: LayoutResult) -> tuple[float, float]:
    """Return (content_width, content_height) of the laid-out boxes."""
    max_x = max(b.x + b.width for b in boxes.values())
    max_y = max(b.y + b.height for b in boxes.values())
    return max_x, max_y


def _document(width: float, height: float, pad: float, theme: Theme,
              body: str) -> str:
    """Wrap ``body`` in a sized <svg> document with background."""
    w = width + pad * 2
    h = height + pad * 2
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}">\n'
        f'  <rect x="0" y="0" width="{w:g}" height="{h:g}" '
        f'fill="{theme.bg}"/>\n'
        f'  <g transform="translate({pad:g}, {pad:g})">\n'
        f'{body}\n'
        f'  </g>\n'
        f'</svg>\n'
    )


def _styles(theme: Theme) -> str:
    return (
        "  <style>\n"
        f"    .mm-text {{ fill: {theme.ink}; font-family: {theme.font_family}; "
        f"font-size: {theme.font_size:g}px; }}\n"
        f"    .mm-root-text {{ fill: {theme.root_text}; "
        f"font-family: {theme.font_family}; "
        f"font-size: {theme.font_size:g}px; font-weight: 600; }}\n"
        "  </style>"
    )


def _nodes(mindmap: MindMap, boxes: LayoutResult, *,
           theme: Theme, style_map: StyleMap | None) -> str:
    parts: list[str] = []
    for node in mindmap.walk():
        if node.id not in boxes:
            continue
        rs = resolve(node.id, is_root=(node is mindmap.root),
                     theme=theme, style_map=style_map)
        parts.append(_node_shape(node, boxes[node.id], rs))
    return "\n".join(parts)


def _node_shape(node: Node, box: Box, rs) -> str:
    label = escape(node.text) or " "
    return (
        f'    <rect x="{box.x:g}" y="{box.y:g}" width="{box.width:g}" '
        f'height="{box.height:g}" rx="{rs.border_radius:g}" '
        f'fill="{rs.fill}" '
        f'stroke="{rs.stroke_none}" '
        f'stroke-width="{DEFAULT_THEME.stroke_width:g}"/>\n'
        f'    <text class="{rs.text_class}" x="{box.cx:g}" '
        f'y="{box.cy + rs.text_baseline_offset:g}" '
        f'text-anchor="middle">{label}</text>'
    )


def _connectors(root: Node, boxes: LayoutResult, *, theme: Theme) -> str:
    """Emit a Bezier curve for every parent->child edge."""
    parts: list[str] = []
    for parent in root.walk():
        if parent.is_leaf or parent.id not in boxes:
            continue
        pbox = boxes[parent.id]
        for child in parent.children:
            if child.id not in boxes:
                continue
            parts.append(_connector(pbox, boxes[child.id], theme=theme))
    return "\n".join(parts)


def _connector(parent: Box, child: Box, *, theme: Theme) -> str:
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
        f'fill="none" stroke="{theme.connector}" '
        f'stroke-width="{theme.stroke_width:g}"/>'
    )
