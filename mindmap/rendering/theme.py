"""Theme — the default visual palette and per-node style resolution.

The theme owns all the "module-level constants" that used to live in
svg.py.  Separating them here makes the renderer testable with custom
palettes and lets a future UI offer theme switching.

:func:`resolve` merges theme defaults with optional per-node overrides
(:class:`~mindmap.domain.style.NodeStyle`) and returns a concrete
:class:`ResolvedStyle` with no ``None`` fields — the renderer never has
to check for missing values.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mindmap.domain.style import NodeStyle, StyleMap

# --------------------------------------------------------------------------- #
#  Theme — global defaults (conceptually immutable after construction)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Theme:
    """The complete visual palette for the mind-map renderer.

    Every renderer output uses these values as the baseline; per-node
    overrides in a :class:`~mindmap.domain.style.StyleMap` can selectively
    replace fields for individual nodes.
    """

    # Canvas
    bg: str = "#fafafa"
    padding: float = 24.0

    # Root node
    root_fill: str = "#1f2933"
    root_text: str = "#ffffff"
    root_rx: float = 8.0

    # Regular node
    node_fill: str = "#ffffff"
    node_stroke: str = "#c3cad2"
    node_rx: float = 6.0

    # Connector
    connector: str = "#9aa5b1"

    # Shared
    ink: str = "#1f2933"
    subtle: str = "#9aa5b1"
    stroke_width: float = 1.2
    font_family: str = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', "
                        "Roboto, 'Helvetica Neue', Arial, 'PingFang SC', "
                        "'Microsoft YaHei', sans-serif")
    font_size: float = 14.0

    # --- label ---
    font_weight: str = "400"
    font_style: str = "normal"
    text_decoration: str = "none"
    text_align: str = "center"


# Default instance — used when the caller provides no explicit theme.
DEFAULT_THEME = Theme()


# --------------------------------------------------------------------------- #
#  ResolvedStyle — final per-node values (all fields concrete, no None)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ResolvedStyle:
    """Fully resolved visual attributes for *one* node.

    Every field is guaranteed non-``None`` — the renderer uses these
    directly without fallback logic.
    """

    fill: str
    stroke: str
    text_color: str
    font_size: float
    font_weight: str
    font_style: str
    text_decoration: str
    text_align: str
    border_radius: float
    is_root: bool

    # Derived helpers (used directly by the SVG renderer)
    @property
    def text_class(self) -> str:
        return "mm-root-text" if self.is_root else "mm-text"

    @property
    def text_baseline_offset(self) -> float:
        """Vertical offset from ``box.cy`` to the text baseline."""
        return self.font_size * 0.35

    @property
    def stroke_none(self) -> str:
        return "none" if self.is_root else self.stroke


# --------------------------------------------------------------------------- #
#  resolve — merge theme + per-node overrides
# --------------------------------------------------------------------------- #


def resolve(node_id: str, *,
            is_root: bool,
            theme: Theme = DEFAULT_THEME,
            style_map: StyleMap | None = None) -> ResolvedStyle:
    """Compute the final visual style for a single node.

    Starts from *theme* defaults, then overlays any per-node override
    found in *style_map* (only non-``None`` fields from the override take
    effect).
    """
    over = style_map.get(node_id) if style_map is not None else None

    def _pick(field: str, theme_val, style_attr: str | None = None):
        if over is not None:
            ov = getattr(over, style_attr or field, None)
            if ov is not None:
                return ov
        return theme_val

    if is_root:
        fill = _pick("fill", theme.root_fill, "fill")
        stroke = _pick("stroke", "none", "stroke")
        text_color = _pick("text_color", theme.root_text, "text_color")
        border_radius = _pick("border_radius", theme.root_rx, "border_radius")
    else:
        fill = _pick("fill", theme.node_fill, "fill")
        stroke = _pick("stroke", theme.node_stroke, "stroke")
        text_color = _pick("text_color", theme.ink, "text_color")
        border_radius = _pick("border_radius", theme.node_rx, "border_radius")

    font_size = _pick("font_size", theme.font_size)
    font_weight = _pick("font_weight", theme.font_weight)
    font_style = _pick("font_style", theme.font_style)
    text_decoration = _pick("text_decoration", theme.text_decoration)
    text_align = _pick("text_align", theme.text_align)

    return ResolvedStyle(
        fill=fill,
        stroke=stroke,
        text_color=text_color,
        font_size=font_size,
        font_weight=font_weight,
        font_style=font_style,
        text_decoration=text_decoration,
        text_align=text_align,
        border_radius=border_radius,
        is_root=is_root,
    )
