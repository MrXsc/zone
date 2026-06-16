"""Rendering layer — draw a laid-out mind map to a concrete output.

The skeleton ships one renderer: SVG (vector, browser-openable, trivial
to produce from strings). A PNG/PDF renderer or a DOM renderer for a
future Web UI would be a sibling here.

This layer depends on domain (for tree walking) and layout (for the
contract Box/LayoutResult). It must not depend on application or
presentation.

Dependencies: domain, layout.
"""

from mindmap.rendering.svg import render_svg

__all__ = ["render_svg"]
