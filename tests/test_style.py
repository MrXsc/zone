"""Tests for M4 style layer (StyleMap, resolve, serialization compat)."""

import json
import tempfile
import unittest
from pathlib import Path

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.domain.style import NodeStyle, StyleMap
from mindmap.rendering.theme import DEFAULT_THEME, Theme, resolve


# =========================================================================== #
#  StyleMap
# =========================================================================== #

class TestStyleMap(unittest.TestCase):

    def setUp(self) -> None:
        self.sm = StyleMap()

    def test_get_returns_none_for_missing(self):
        self.assertIsNone(self.sm.get("nonexistent"))

    def test_set_and_get(self):
        s = NodeStyle(fill="#ff0")
        self.sm.set("n1", s)
        self.assertIs(self.sm.get("n1"), s)

    def test_remove(self):
        self.sm.set("n1", NodeStyle(fill="#ff0"))
        self.sm.remove("n1")
        self.assertIsNone(self.sm.get("n1"))

    def test_remove_nonexistent_is_noop(self):
        self.sm.remove("nope")   # should not raise

    def test_to_dict_skips_none_fields(self):
        self.sm.set("n1", NodeStyle(fill="#ff0", stroke=None))
        d = self.sm.to_dict()
        self.assertEqual(d, {"n1": {"fill": "#ff0"}})

    def test_to_dict_empty(self):
        self.assertEqual(self.sm.to_dict(), {})

    def test_from_dict_roundtrip(self):
        self.sm.set("a", NodeStyle(fill="#ff0", font_size=16.0))
        data = self.sm.to_dict()
        restored = StyleMap.from_dict(data)
        self.assertEqual(restored.get("a"), NodeStyle(fill="#ff0",
                                                       font_size=16.0))

    def test_from_dict_ignores_unknown_keys(self):
        """Extra keys in the dict are silently dropped."""
        raw = {"n1": {"fill": "#ff0", "unknown_attr": "x"}}
        sm = StyleMap.from_dict(raw)
        self.assertEqual(sm.get("n1"), NodeStyle(fill="#ff0"))


# =========================================================================== #
#  resolve()
# =========================================================================== #

class TestResolve(unittest.TestCase):
    """Theme + optional StyleMap → ResolvedStyle."""

    def test_resolve_without_style_map_uses_theme_defaults(self):
        rs = resolve("r", is_root=True, theme=DEFAULT_THEME, style_map=None)
        self.assertEqual(rs.fill, DEFAULT_THEME.root_fill)
        self.assertEqual(rs.stroke, "none")
        self.assertEqual(rs.text_color, DEFAULT_THEME.root_text)

        rs2 = resolve("n", is_root=False, theme=DEFAULT_THEME, style_map=None)
        self.assertEqual(rs2.fill, DEFAULT_THEME.node_fill)
        self.assertEqual(rs2.stroke, DEFAULT_THEME.node_stroke)

    def test_resolve_root_with_style_override(self):
        sm = StyleMap()
        sm.set("r", NodeStyle(fill="#f00", font_size=20.0))
        rs = resolve("r", is_root=True, theme=DEFAULT_THEME, style_map=sm)
        self.assertEqual(rs.fill, "#f00")
        self.assertEqual(rs.font_size, 20.0)
        # Non-overridden fields still come from theme
        self.assertEqual(rs.text_color, DEFAULT_THEME.root_text)

    def test_resolve_child_with_style_override(self):
        sm = StyleMap()
        sm.set("c", NodeStyle(stroke="#abc", border_radius=99.0))
        rs = resolve("c", is_root=False, theme=DEFAULT_THEME, style_map=sm)
        self.assertEqual(rs.stroke, "#abc")
        self.assertEqual(rs.border_radius, 99.0)
        # Unchanged fields stay at theme defaults
        self.assertEqual(rs.fill, DEFAULT_THEME.node_fill)

    def test_resolve_untouched_node_uses_theme(self):
        sm = StyleMap()
        sm.set("other", NodeStyle(fill="#f00"))
        rs = resolve("untouched", is_root=False, theme=DEFAULT_THEME,
                      style_map=sm)
        self.assertEqual(rs.fill, DEFAULT_THEME.node_fill)

    def test_text_baseline_offset_scales_with_font_size(self):
        sm = StyleMap()
        sm.set("n", NodeStyle(font_size=24.0))
        rs = resolve("n", is_root=False, theme=DEFAULT_THEME, style_map=sm)
        self.assertAlmostEqual(rs.text_baseline_offset, 24.0 * 0.35)

    def test_resolve_with_different_theme(self):
        dark = Theme(bg="#000", ink="#fff", root_fill="#333",
                     node_fill="#222", node_stroke="#555")
        rs = resolve("n", is_root=False, theme=dark, style_map=None)
        self.assertEqual(rs.fill, "#222")
        self.assertEqual(rs.stroke, "#555")
        self.assertEqual(rs.text_color, "#fff")


# =========================================================================== #
#  MindMap — styled serialization
# =========================================================================== #

class TestMindMapStyles(unittest.TestCase):
    """MindMap with optional StyleMap → to_dict / from_dict."""

    def test_plain_mindmap_to_dict_has_no_styles_key(self):
        mm = MindMap.new("t", "root")
        d = mm.to_dict()
        self.assertNotIn("styles", d)

    def test_styled_mindmap_to_dict_includes_styles(self):
        mm = MindMap.new("t", "root")
        child = mm.root.add_child(Node.create("c"))
        mm.set_style(child.id, fill="#ff0")
        d = mm.to_dict()
        self.assertIn("styles", d)
        self.assertIn(child.id, d["styles"])

    def test_styled_mindmap_roundtrip(self):
        mm = MindMap.new("t", "root")
        child = mm.root.add_child(Node.create("c"))
        mm.set_style(child.id, fill="#abc", font_size=18.0)
        data = mm.to_dict()
        restored = MindMap.from_dict(data)
        self.assertEqual(restored.title, mm.title)
        self.assertEqual(restored.root.text, mm.root.text)
        self.assertIsNotNone(restored.styles)
        s = restored.styles.get(child.id)
        self.assertIsNotNone(s)
        self.assertEqual(s.fill, "#abc")
        self.assertEqual(s.font_size, 18.0)

    def test_old_file_without_styles_still_loads(self):
        """Backward compat: a dict without 'styles' gets styles=None."""
        data = {
            "id": "old",
            "title": "Legacy",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "root": {"id": "r", "text": "root", "children": []},
        }
        mm = MindMap.from_dict(data)
        self.assertIsNone(mm.styles)

    def test_styles_survives_json_roundtrip(self):
        """Simulate real file save/load via JSON."""
        mm = MindMap.new("t", "root")
        child = mm.root.add_child(Node.create("c"))
        mm.set_style(child.id, fill="#f00")
        json_str = json.dumps(mm.to_dict(), ensure_ascii=False)
        loaded = MindMap.from_dict(json.loads(json_str))
        s = loaded.styles.get(child.id) if loaded.styles else None
        self.assertIsNotNone(s)
        self.assertEqual(s.fill, "#f00")


# =========================================================================== #
#  SVG renderer — visual regression with styles
# =========================================================================== #

from mindmap.layout import layout
from mindmap.rendering.svg import render_svg


class TestStyledRendering(unittest.TestCase):
    """Rendering with style_map produces correct visual output."""

    def _mm(self) -> MindMap:
        mm = MindMap.new("t", "root")
        mm.root.add_child(Node.create("child"))
        return mm

    def test_style_map_none_produces_same_output(self):
        """style_map=None should match the default (no-style) output."""
        mm = self._mm()
        boxes = layout(mm)
        svg_default = render_svg(mm, boxes)
        svg_explicit = render_svg(mm, boxes, style_map=None)
        self.assertEqual(svg_default, svg_explicit)

    def test_style_map_empty_produces_same_output(self):
        mm = self._mm()
        boxes = layout(mm)
        svg_default = render_svg(mm, boxes)
        svg_empty = render_svg(mm, boxes, style_map=StyleMap())
        self.assertEqual(svg_default, svg_empty)

    def test_style_override_appears_in_svg(self):
        mm = self._mm()
        child = mm.root.children[0]
        mm.set_style(child.id, fill="#abc123")
        boxes = layout(mm)
        svg = render_svg(mm, boxes, style_map=mm.styles)
        self.assertIn("#abc123", svg)
        # Root should still have default fill
        self.assertIn(DEFAULT_THEME.root_fill, svg)


if __name__ == "__main__":
    unittest.main()
