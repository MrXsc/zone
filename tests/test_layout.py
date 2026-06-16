"""Tests for the balanced-tree layout."""

import unittest

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.layout import LayoutOptions, layout
from mindmap.layout.contract import Box


def _mm(children_texts: list[str]) -> MindMap:
    mm = MindMap.new("t", "root")
    for t in children_texts:
        mm.root.add_child(Node.create(t))
    return mm


def _overlap(a: Box, b: Box) -> bool:
    return not (a.x + a.width <= b.x or b.x + b.width <= a.x
                or a.y + a.height <= b.y or b.y + b.height <= a.y)


class TestLayoutBasics(unittest.TestCase):
    def test_root_present_and_at_origin_after_normalize(self):
        mm = _mm(["a", "b", "c"])
        boxes = layout(mm)
        self.assertIn(mm.root.id, boxes)
        # After normalization min x/y == 0; root may not be at (0,0) but
        # something touches the origin.
        xs = [b.x for b in boxes.values()]
        ys = [b.y for b in boxes.values()]
        self.assertAlmostEqual(min(xs), 0.0)
        self.assertAlmostEqual(min(ys), 0.0)

    def test_every_node_has_a_box(self):
        mm = _mm(["a", "b"])
        mm.root.children[0].add_child(Node.create("a1"))
        boxes = layout(mm)
        ids = {n.id for n in mm.walk()}
        self.assertEqual(set(boxes.keys()), ids)

    def test_all_boxes_nonnegative(self):
        mm = _mm(["a", "b", "c", "d"])
        boxes = layout(mm)
        for b in boxes.values():
            self.assertGreaterEqual(b.x, 0.0)
            self.assertGreaterEqual(b.y, 0.0)


class TestBalancedSplit(unittest.TestCase):
    def test_children_split_left_and_right(self):
        """With an even number of root children, half go each side."""
        mm = _mm(["a", "b", "c", "d"])  # 4 children
        boxes = layout(mm)
        root_box = boxes[mm.root.id]
        right = 0
        left = 0
        for c in mm.root.children:
            cb = boxes[c.id]
            if cb.x >= root_box.x:
                right += 1
            else:
                left += 1
        self.assertEqual(left, 2)
        self.assertEqual(right, 2)

    def test_no_sibling_overlaps_vertically(self):
        """Siblings on the same side must not overlap."""
        mm = _mm(["a", "b", "c", "d"])
        boxes = layout(mm)
        root_box = boxes[mm.root.id]
        same_side: list[list[Box]] = [[], []]
        for c in mm.root.children:
            cb = boxes[c.id]
            side = 0 if cb.x < root_box.x else 1
            same_side[side].append(cb)
        for group in same_side:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    self.assertFalse(_overlap(group[i], group[j]),
                                     "Sibling boxes overlap")

    def test_parent_centered_on_children(self):
        """A parent sits between its children vertically (within tolerance)."""
        mm = MindMap.new("t", "root")
        for t in ("a", "b"):
            mm.root.add_child(Node.create(t))
        boxes = layout(mm)
        # Root's vertical center should sit between its two children's centers.
        root_cy = boxes[mm.root.id].cy
        child_cys = sorted(boxes[c.id].cy for c in mm.root.children)
        self.assertLessEqual(child_cys[0], root_cy + 0.5)
        self.assertGreaterEqual(child_cys[1], root_cy - 0.5)


class TestOptions(unittest.TestCase):
    def test_custom_options_affect_sizes(self):
        mm = _mm(["longtext"])
        small = layout(mm, LayoutOptions(char_width=5.0))
        big = layout(mm, LayoutOptions(char_width=20.0))
        # Bigger char width -> wider child box.
        small_w = small[mm.root.children[0].id].width
        big_w = big[mm.root.children[0].id].width
        self.assertGreater(big_w, small_w)


class TestDeepTree(unittest.TestCase):
    def test_deep_tree_no_overlap_and_balanced(self):
        """A multi-level tree lays out without overlapping siblings."""
        mm = MindMap.new("t", "root")
        for branch in ("L1", "L2", "R1", "R2"):
            b = mm.root.add_child(Node.create(branch))
            b.add_child(Node.create(branch + ".a"))
            b.add_child(Node.create(branch + ".b"))
        boxes = layout(mm)

        # No parent->child pair of siblings overlap within any subtree.
        for node in mm.walk():
            kids = [boxes[c.id] for c in node.children]
            for i in range(len(kids)):
                for j in range(i + 1, len(kids)):
                    # Only assert vertical separation for siblings at same
                    # horizontal band is enough; here full overlap check.
                    self.assertFalse(_overlap(kids[i], kids[j]))


if __name__ == "__main__":
    unittest.main()
