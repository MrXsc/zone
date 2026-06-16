"""Tests for Markdown bidirectional conversion."""

import unittest

from mindmap.convert.markdown import from_markdown, to_markdown
from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node


def _tree() -> MindMap:
    mm = MindMap.new("Demo", "root")
    a = mm.root.add_child(Node.create("branch1"))
    a.add_child(Node.create("leaf1"))
    a.add_child(Node.create("leaf2"))
    mm.root.add_child(Node.create("branch2"))
    return mm


class TestToMarkdown(unittest.TestCase):
    def test_emits_title_and_bullets(self):
        md = to_markdown(_tree())
        lines = md.splitlines()
        self.assertEqual(lines[0], "# Demo")
        self.assertEqual(lines[1], "")  # blank separator
        self.assertEqual(lines[2], "- root")

    def test_nested_indent(self):
        md = to_markdown(_tree())
        self.assertIn("  - branch1", md)
        self.assertIn("    - leaf1", md)

    def test_no_title_when_empty(self):
        mm = MindMap.new("", "only")
        md = to_markdown(mm)
        self.assertEqual(md.strip(), "- only")


class TestFromMarkdown(unittest.TestCase):
    def test_parses_title_and_structure(self):
        md = "# Demo\n\n- root\n  - branch1\n    - leaf1\n  - branch2\n"
        mm = from_markdown(md)
        self.assertEqual(mm.title, "Demo")
        self.assertEqual(mm.root.text, "root")
        self.assertEqual([c.text for c in mm.root.children],
                         ["branch1", "branch2"])
        self.assertEqual([c.text for c in mm.root.children[0].children],
                         ["leaf1"])

    def test_tolerates_4_space_indent(self):
        md = "- root\n    - child\n        - grand\n"
        mm = from_markdown(md)
        self.assertEqual(mm.root.text, "root")
        self.assertEqual(mm.root.children[0].text, "child")
        self.assertEqual(mm.root.children[0].children[0].text, "grand")

    def test_tolerates_tabs(self):
        md = "- root\n\t- child\n"
        mm = from_markdown(md)
        self.assertEqual(len(mm.root.children), 1)

    def test_no_root_raises(self):
        with self.assertRaises(ValueError):
            from_markdown("# Title only\n\nsome prose")

    def test_multiple_roots_raises(self):
        md = "- root1\n- root2\n"
        with self.assertRaises(ValueError):
            from_markdown(md)

    def test_explicit_title_overrides(self):
        md = "- root\n"
        mm = from_markdown(md, title="Custom")
        self.assertEqual(mm.title, "Custom")


class TestRoundtrip(unittest.TestCase):
    def test_structure_survives_roundtrip(self):
        original = _tree()
        md = to_markdown(original)
        restored = from_markdown(md)
        # Text + structure preserved (ids intentionally NOT).
        self.assertEqual(_structure(original.root), _structure(restored.root))
        self.assertEqual(restored.title, original.title)

    def test_roundtrip_ids_regenerated(self):
        """Markdown is lossy: ids must not survive (they're regenerated)."""
        original = _tree()
        restored = from_markdown(to_markdown(original))
        self.assertNotEqual(original.root.id, restored.root.id)


def _structure(node: Node) -> tuple:
    """A text/shape signature that ignores ids."""
    return (node.text, tuple(_structure(c) for c in node.children))


if __name__ == "__main__":
    unittest.main()
