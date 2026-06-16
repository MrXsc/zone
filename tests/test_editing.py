"""Tests for M3 editing (domain mutators, service wrappers, CLI commands)."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mindmap.domain.node import Node
from mindmap.domain.mindmap import MindMap
from mindmap.application.services import MindMapService
from mindmap.presentation.cli import main
from mindmap.storage.json_repository import JsonFileRepository


# =========================================================================== #
#  Domain — Node mutators
# =========================================================================== #

class TestNodeMutators(unittest.TestCase):
    """set_text, update_note, remove_child, reorder_children, index_of."""

    def setUp(self) -> None:
        self.root = Node.create("root")
        self.a = self.root.add_child(Node.create("a"))
        self.b = self.root.add_child(Node.create("b"))

    # -- set_text ------------------------------------------------------------

    def test_set_text_returns_self(self):
        ret = self.root.set_text("new")
        self.assertIs(ret, self.root)

    def test_set_text_changes_text(self):
        self.root.set_text("changed")
        self.assertEqual(self.root.text, "changed")

    # -- update_note ---------------------------------------------------------

    def test_update_note_sets_note(self):
        self.root.update_note("hello")
        self.assertEqual(self.root.note, "hello")

    def test_update_note_returns_self(self):
        ret = self.root.update_note("x")
        self.assertIs(ret, self.root)

    # -- remove_child --------------------------------------------------------

    def test_remove_child_by_object(self):
        removed = self.root.remove_child(self.a)
        self.assertIs(removed, self.a)
        self.assertEqual(self.root.children, [self.b])

    def test_remove_child_by_id(self):
        removed = self.root.remove_child(self.a.id)
        self.assertIs(removed, self.a)

    def test_remove_child_not_found_returns_none(self):
        ret = self.root.remove_child("nonexistent")
        self.assertIsNone(ret)

    def test_remove_child_not_immediate_returns_none(self):
        grand = self.a.add_child(Node.create("grand"))
        ret = self.root.remove_child(grand)   # grand is not a direct child
        self.assertIsNone(ret)

    # -- index_of ------------------------------------------------------------

    def test_index_of_by_object(self):
        self.assertEqual(self.root.index_of(self.a), 0)
        self.assertEqual(self.root.index_of(self.b), 1)

    def test_index_of_by_id(self):
        self.assertEqual(self.root.index_of(self.a.id), 0)

    def test_index_of_not_found_raises(self):
        with self.assertRaises(ValueError):
            self.root.index_of("nonexistent")

    # -- reorder_children ----------------------------------------------------

    def test_reorder_children(self):
        self.root.reorder_children([self.b.id, self.a.id])
        self.assertEqual(self.root.children, [self.b, self.a])

    def test_reorder_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.root.reorder_children(["bad", self.a.id])

    def test_reorder_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            self.root.reorder_children([self.a.id, self.a.id])

    def test_reorder_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            self.root.reorder_children([self.a.id])


# =========================================================================== #
#  Domain — MindMap editing
# =========================================================================== #

class TestMindMapEditing(unittest.TestCase):
    """add_child, update_node, remove, move + cycle protection."""

    def setUp(self) -> None:
        self.mm = MindMap.new("Test", "root")
        self.child = self.mm.root.add_child(Node.create("child"))
        self.grand = self.child.add_child(Node.create("grand"))

    # -- add_child -----------------------------------------------------------

    def test_add_child_creates_node_under_parent(self):
        new_id = self.mm.add_child(self.child.id, "leaf")
        node = self.mm.find(new_id.id)
        self.assertIsNotNone(node)
        self.assertEqual(node.text, "leaf")
        self.assertIs(self.child.find(node.id), node)

    def test_add_child_nonexistent_parent_raises(self):
        with self.assertRaises(ValueError):
            self.mm.add_child("bad", "x")

    # -- update_node ---------------------------------------------------------

    def test_update_node_text(self):
        self.mm.update_node(self.child.id, text="new")
        self.assertEqual(self.child.text, "new")

    def test_update_node_note(self):
        self.mm.update_node(self.child.id, note="n1")
        self.assertEqual(self.child.note, "n1")

    def test_update_node_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.mm.update_node("bad", text="x")

    def test_update_node_keeps_fields_not_passed(self):
        self.child.note = "original"
        self.mm.update_node(self.child.id, text="new")
        self.assertEqual(self.child.note, "original")

    # -- remove --------------------------------------------------------------

    def test_remove_detaches_subtree(self):
        removed = self.mm.remove(self.child.id)
        self.assertIsNotNone(removed)
        self.assertEqual(removed.text, "child")
        self.assertEqual(self.mm.root.children, [])   # child was only one

    def test_remove_nonexistent_returns_none(self):
        ret = self.mm.remove("nonexistent")
        self.assertIsNone(ret)

    def test_remove_root_raises(self):
        with self.assertRaises(ValueError):
            self.mm.remove(self.mm.root.id)

    def test_remove_leaf(self):
        removed = self.mm.remove(self.grand.id)
        self.assertIsNotNone(removed)
        self.assertEqual(self.child.children, [])

    # -- move ----------------------------------------------------------------

    def test_move_child_under_sibling(self):
        # Create a second top-level child
        c2 = self.mm.root.add_child(Node.create("c2"))
        self.mm.move(self.child.id, c2.id)
        self.assertIn(self.child, c2.children)
        self.assertNotIn(self.child, self.mm.root.children)

    def test_move_to_self_raises(self):
        with self.assertRaises(ValueError):
            self.mm.move(self.child.id, self.child.id)

    def test_move_to_descendant_raises(self):
        with self.assertRaises(ValueError):
            self.mm.move(self.child.id, self.grand.id)  # child -> grand = cycle

    def test_move_root_raises(self):
        with self.assertRaises(ValueError):
            self.mm.move(self.mm.root.id, self.child.id)

    def test_move_nonexistent_node_raises(self):
        with self.assertRaises(ValueError):
            self.mm.move("bad", self.child.id)

    def test_move_to_nonexistent_parent_raises(self):
        with self.assertRaises(ValueError):
            self.mm.move(self.child.id, "bad")


# =========================================================================== #
#  Service — thin wrappers
# =========================================================================== #

class TestEditingService(unittest.TestCase):
    """Service wrappers call domain + touch."""

    def setUp(self) -> None:
        self.svc = MindMapService(JsonFileRepository())
        self.mm = self.svc.new("T", "root")
        self.child = self.mm.root.add_child(Node.create("c"))

    def test_service_add_child_touches(self):
        old = self.mm.updated_at
        self.svc.add_child(self.mm, self.child.id, "leaf")
        self.assertGreaterEqual(self.mm.updated_at, old)
        self.assertIsNotNone(self.mm.find(self.child.id + "???") is None)
        # Actually verify the child was added
        leaf = self.mm.find(self.child.children[-1].id)
        self.assertEqual(leaf.text, "leaf")

    def test_service_remove_touches(self):
        old = self.mm.updated_at
        self.svc.remove(self.mm, self.child.id)
        self.assertGreaterEqual(self.mm.updated_at, old)

    def test_service_update_node_touches(self):
        old = self.mm.updated_at
        self.svc.update_node(self.mm, self.child.id, text="x")
        self.assertGreaterEqual(self.mm.updated_at, old)
        self.assertEqual(self.child.text, "x")

    def test_service_move_touches(self):
        c2 = self.mm.root.add_child(Node.create("c2"))
        old = self.mm.updated_at
        self.svc.move(self.mm, self.child.id, c2.id)
        self.assertGreaterEqual(self.mm.updated_at, old)


# =========================================================================== #
#  CLI — editing commands end-to-end
# =========================================================================== #

class TestCliEditing(unittest.TestCase):
    """add, edit, rm, move, ls via the CLI main()."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.doc = self.dir / "test.mm.json"
        # Create a doc with a few nodes
        main(["new", "Editing", "--root", "中心", "-o", str(self.doc)])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _capture(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    # -- add ----------------------------------------------------------------

    def test_add_node(self):
        # First, find the root id via ls
        rc0, ls_out = self._capture(["ls", "--doc", str(self.doc)])
        root_id = ls_out.splitlines()[0].split()[0]  # first line, first token
        rc, out = self._capture(
            ["add", root_id, "分支1", "--doc", str(self.doc)])
        self.assertEqual(rc, 0)
        self.assertIn("Added", out)
        # Verify by re-opening
        mm = MindMapService(JsonFileRepository()).open(self.doc)
        self.assertEqual(mm.count(), 2)

    # -- edit ---------------------------------------------------------------

    def test_edit_node_text(self):
        rc, _ = self._capture(["ls", "--doc", str(self.doc)])
        root_id = _.splitlines()[0].split()[0]
        rc, out = self._capture(
            ["edit", root_id, "--text", "新中心", "--doc", str(self.doc)])
        self.assertEqual(rc, 0)
        self.assertIn("Updated", out)
        mm = MindMapService(JsonFileRepository()).open(self.doc)
        self.assertEqual(mm.root.text, "新中心")

    # -- rm -----------------------------------------------------------------

    def test_rm_node(self):
        # Add a child then remove it
        rc, out = self._capture(["ls", "--doc", str(self.doc)])
        root_id = out.splitlines()[0].split()[0]
        self._capture(["add", root_id, "x", "--doc", str(self.doc)])
        # Find child id
        rc, out2 = self._capture(["ls", "--doc", str(self.doc)])
        child_id = out2.splitlines()[1].split()[0]
        rc_rm, _ = self._capture(["rm", child_id, "--doc", str(self.doc)])
        self.assertEqual(rc_rm, 0)
        mm = MindMapService(JsonFileRepository()).open(self.doc)
        self.assertEqual(mm.count(), 1)  # only root

    def test_rm_root_returns_error(self):
        rc, out = self._capture(["ls", "--doc", str(self.doc)])
        root_id = out.splitlines()[0].split()[0]
        # Suppress stderr; we check rc
        rc_rm, _ = self._capture(["rm", root_id, "--doc", str(self.doc)])
        self.assertEqual(rc_rm, 1)

    # -- move ---------------------------------------------------------------

    def test_move_node(self):
        rc, out = self._capture(["ls", "--doc", str(self.doc)])
        root_id = out.splitlines()[0].split()[0]
        self._capture(["add", root_id, "a", "--doc", str(self.doc)])
        self._capture(["add", root_id, "b", "--doc", str(self.doc)])
        rc, out2 = self._capture(["ls", "--doc", str(self.doc)])
        ids = [line.split()[0] for line in out2.splitlines()
               if line.strip() and not line.startswith("Total")]
        a_id, b_id = ids[1], ids[2]   # skip root
        rc_mv, _ = self._capture(
            ["move", a_id, "--to", b_id, "--doc", str(self.doc)])
        self.assertEqual(rc_mv, 0)

    # -- ls -----------------------------------------------------------------

    def test_ls_shows_all_nodes(self):
        rc, out = self._capture(["ls", "--doc", str(self.doc)])
        self.assertEqual(rc, 0)
        self.assertIn("中心", out)       # root text
        self.assertIn("Total:", out)     # summary line

    def test_ls_with_empty_doc_shows_root(self):
        rc, out = self._capture(["ls", "--doc", str(self.doc)])
        self.assertIn("中心", out)
        self.assertIn("Total: 1", out)


if __name__ == "__main__":
    unittest.main()
