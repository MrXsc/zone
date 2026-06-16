"""Tests for the domain model (Node, MindMap)."""

import unittest

from mindmap.domain.node import Node
from mindmap.domain.mindmap import MindMap


class TestNode(unittest.TestCase):
    def test_create_assigns_unique_id(self):
        a = Node.create("a")
        b = Node.create("b")
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(a.text, "a")

    def test_add_child_appends_in_order(self):
        root = Node.create("root")
        c1 = root.add_child(Node.create("1"))
        c2 = root.add_child(Node.create("2"))
        self.assertEqual(root.children, [c1, c2])
        self.assertTrue(c1.is_leaf)

    def test_add_child_with_index(self):
        root = Node.create("root")
        root.add_child(Node.create("1"))
        middle = Node.create("mid")
        root.add_child(middle, index=0)
        self.assertIs(root.children[0], middle)

    def test_walk_is_preorder(self):
        root = Node.create("root")
        a = root.add_child(Node.create("a"))
        a.add_child(Node.create("a1"))
        root.add_child(Node.create("b"))
        texts = [n.text for n in root.walk()]
        self.assertEqual(texts, ["root", "a", "a1", "b"])

    def test_find_by_id(self):
        root = Node.create("root")
        child = root.add_child(Node.create("c"))
        self.assertIs(root.find(child.id), child)
        self.assertIsNone(root.find("nonexistent"))

    def test_find_parent(self):
        root = Node.create("root")
        child = root.add_child(Node.create("c"))
        grand = child.add_child(Node.create("g"))
        self.assertIs(root.find_parent(child.id), root)
        self.assertIs(root.find_parent(grand.id), child)
        # Root's parent is None.
        self.assertIsNone(root.find_parent(root.id))

    def test_count_includes_self(self):
        root = Node.create("root")
        root.add_child(Node.create("a"))
        root.add_child(Node.create("b"))
        self.assertEqual(root.count(), 3)

    def test_to_from_dict_roundtrip(self):
        root = Node.create("root", note="n")
        root.add_child(Node.create("a"))
        data = root.to_dict()
        restored = Node.from_dict(data)
        self.assertEqual(restored.to_dict(), data)

    def test_clone_has_new_ids(self):
        root = Node.create("root")
        root.add_child(Node.create("a"))
        clone = root.clone()
        self.assertNotEqual(clone.id, root.id)
        self.assertEqual(len(clone.children), 1)
        self.assertNotEqual(clone.children[0].id, root.children[0].id)


class TestMindMap(unittest.TestCase):
    def test_new_creates_single_root(self):
        mm = MindMap.new("t", "root")
        self.assertEqual(mm.title, "t")
        self.assertEqual(mm.root.text, "root")
        self.assertEqual(mm.count(), 1)
        self.assertTrue(mm.root.is_leaf)

    def test_touch_updates_timestamp(self):
        mm = MindMap.new("t", "root")
        old = mm.updated_at
        mm.touch()
        self.assertGreaterEqual(mm.updated_at, old)

    def test_delegation(self):
        mm = MindMap.new("t", "root")
        child = mm.root.add_child(Node.create("c"))
        self.assertIs(mm.find(child.id), child)
        self.assertEqual(mm.count(), 2)
        self.assertEqual(len(list(mm.walk())), 2)

    def test_to_from_dict_roundtrip(self):
        mm = MindMap.new("t", "root")
        mm.root.add_child(Node.create("a"))
        mm.root.add_child(Node.create("b"))
        data = mm.to_dict()
        restored = MindMap.from_dict(data)
        self.assertEqual(restored.to_dict(), data)


if __name__ == "__main__":
    unittest.main()
