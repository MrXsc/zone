"""Layout data contracts — shared between strategies and the renderer.

Box uses top-left origin with +y downward (the SVG/screen convention),
so the renderer can draw boxes with no coordinate flipping.

All units are abstract "layout units" — the renderer may scale them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """An axis-aligned rectangle for one node.

    Attributes:
        x, y:    top-left corner.
        width:   box width (text-fitting estimate from the layout).
        height:  box height (fixed per row in the skeleton).
    """

    x: float
    y: float
    width: float
    height: float

    @property
    def cx(self) -> float:
        """Horizontal center."""
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        """Vertical center."""
        return self.y + self.height / 2


# A layout is just "which box does each node id get". A plain dict keeps
# the contract trivial and JSON-serializable if a renderer wants that.
LayoutResult = dict[str, Box]


@dataclass(frozen=True)
class LayoutOptions:
    """Knobs for the balanced-tree layout.

    Tuned for a clean, readable default. All values are in layout units.

    Attributes:
        node_height:     height of every node box.
        min_node_width:  floor for box width (short labels).
        char_width:      estimated width per character (sans-serif ~6-7px).
        h_padding:       inner left/right text padding inside a box.
        sibling_gap:     vertical gap between sibling boxes.
        level_gap:       horizontal gap between a parent and its children.
    """

    node_height: float = 34.0
    min_node_width: float = 90.0
    char_width: float = 9.0
    h_padding: float = 22.0
    sibling_gap: float = 12.0
    level_gap: float = 90.0
