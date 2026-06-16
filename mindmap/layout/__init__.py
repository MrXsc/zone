"""Layout layer — turn a tree into 2D box coordinates.

This layer is pure geometry: it knows nothing about pixels on screen,
SVG, or fonts. It consumes a MindMap and produces a LayoutResult (a map
of node id -> Box). The renderer then draws boxes however it likes.

The skeleton ships one strategy (balanced left/right tree). Other
strategies (radial, top-down) can be added as siblings without touching
the renderer or the domain.

Dependencies: domain only.
"""

from mindmap.layout.contract import Box, LayoutResult, LayoutOptions
from mindmap.layout.balanced_tree import layout

__all__ = ["Box", "LayoutResult", "LayoutOptions", "layout"]
