"""Style layer — optional per-node visual overrides.

Kept separate from Node (as promised in node.py's design note) so the core
model stays minimal and the style system can evolve independently.

StyleMap is a flat ``node_id -> NodeStyle`` dict attached to MindMap.
A missing entry means "use theme default" — no style, no overhead.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeStyle:
    """Per-node visual overrides.  ``None`` = inherit from theme default.

    Only the fields that make sense for individual node override are
    included here.  Global-level knobs (canvas background, connector
    color, …) belong in :class:`~mindmap.rendering.theme.Theme`.
    """

    fill: str | None = None
    stroke: str | None = None
    text_color: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    border_radius: float | None = None


@dataclass
class StyleMap:
    """A mutable mapping of node_id → NodeStyle.

    A ``StyleMap`` with an empty *styles* dict is the same as no style
    at all — every node renders with theme defaults.
    """

    styles: dict[str, NodeStyle] = field(default_factory=dict)

    def get(self, node_id: str) -> NodeStyle | None:
        """Return the style for *node_id*, or ``None``."""
        return self.styles.get(node_id)

    def set(self, node_id: str, style: NodeStyle) -> None:
        """Assign a style to *node_id*."""
        self.styles[node_id] = style

    def remove(self, node_id: str) -> None:
        """Clear the style for *node_id* (no-op if not present)."""
        self.styles.pop(node_id, None)

    # ---- serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, dict]:
        return {
            nid: {k: v for k, v in _asdict(s).items() if v is not None}
            for nid, s in self.styles.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, dict]) -> "StyleMap":
        styles: dict[str, NodeStyle] = {}
        for nid, raw in data.items():
            kwargs = {k: v for k, v in raw.items()
                      if k in NodeStyle.__dataclass_fields__}
            styles[nid] = NodeStyle(**kwargs)
        return cls(styles=styles)


def _asdict(obj) -> dict:
    """Minimal ``dataclasses.asdict`` — no deep recursion needed."""
    return {f.name: getattr(obj, f.name) for f in obj.__dataclass_fields__.values()}
