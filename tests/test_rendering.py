"""Tests for the SVG renderer."""

import unittest

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.layout import layout
from mindmap.rendering.svg import render_svg


def _mm() -> MindMap:
    mm = MindMap.new("Demo", "root")
    a = mm.root.add_child(Node.create("branch1"))
    a.add_child(Node.create("leaf1"))
    mm.root.add_child(Node.create("branch2"))
    return mm


class TestSvgOutput(unittest.TestCase):
    def test_is_valid_svg_document(self):
        svg = render_svg(_mm(), layout(_mm()))
        self.assertTrue(svg.startswith('<?xml'))
        self.assertIn("<svg", svg)
        self.assertTrue(svg.rstrip().endswith("</svg>"))

    def test_has_node_for_every_node(self):
        mm = _mm()
        svg = render_svg(mm, layout(mm))
        for node in mm.walk():
            self.assertIn(_escape(node.text), svg)

    def test_has_connector_paths(self):
        mm = _mm()
        svg = render_svg(mm, layout(mm))
        # One path per edge; 3 edges here (root->b1, b1->l1, root->b2).
        path_count = svg.count("<path ")
        self.assertEqual(path_count, 3)

    def test_escapes_special_xml_chars(self):
        mm = MindMap.new("t", "a < b & c")
        svg = render_svg(mm, layout(mm))
        # Raw angle brackets must not appear unescaped in text content.
        self.assertIn("a &lt; b &amp; c", svg)

    def test_empty_layout_produces_valid_svg(self):
        svg = render_svg(MindMap.new("t", "x"), {})
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)


def _escape(s: str) -> str:
    """Mirror the renderer's escaping for assertion lookups."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


if __name__ == "__main__":
    unittest.main()
