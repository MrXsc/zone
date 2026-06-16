"""Tests for the storage layer (JsonFileRepository + Protocol)."""

import json
import tempfile
import unittest
from pathlib import Path

from mindmap.domain.mindmap import MindMap
from mindmap.domain.node import Node
from mindmap.storage.repository import MindMapRepository, RepositoryError
from mindmap.storage.json_repository import JsonFileRepository


def _sample() -> MindMap:
    mm = MindMap.new("Sample", "root")
    mm.root.add_child(Node.create("a"))
    mm.root.add_child(Node.create("b"))
    return mm


class TestJsonRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.repo = JsonFileRepository()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_save_creates_file(self):
        path = self.dir / "m.mm.json"
        self.repo.save(_sample(), path)
        self.assertTrue(path.exists())

    def test_save_load_roundtrip_preserves_structure(self):
        path = self.dir / "m.mm.json"
        original = _sample()
        self.repo.save(original, path)
        loaded = self.repo.load(path)
        self.assertEqual(loaded.to_dict(), original.to_dict())

    def test_roundtrip_preserves_ids(self):
        path = self.dir / "m.mm.json"
        original = _sample()
        self.repo.save(original, path)
        loaded = self.repo.load(path)
        # Node ids must survive a round-trip (lossless format).
        self.assertEqual(loaded.root.id, original.root.id)
        self.assertEqual([c.id for c in loaded.root.children],
                         [c.id for c in original.root.children])

    def test_save_writes_utf8_cjk(self):
        mm = MindMap.new("标题", "中心主题")
        mm.root.add_child(Node.create("分支一"))
        path = self.dir / "cjk.mm.json"
        self.repo.save(mm, path)
        # Raw bytes should contain the UTF-8 characters (not escaped).
        raw = path.read_bytes().decode("utf-8")
        self.assertIn("中心主题", raw)
        self.assertIn("分支一", raw)
        # And load back correctly.
        loaded = self.repo.load(path)
        self.assertEqual(loaded.root.text, "中心主题")

    def test_load_missing_raises(self):
        with self.assertRaises(RepositoryError):
            self.repo.load(self.dir / "nope.mm.json")

    def test_load_corrupt_raises(self):
        path = self.dir / "bad.mm.json"
        path.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(RepositoryError):
            self.repo.load(path)

    def test_load_missing_root_key_raises(self):
        path = self.dir / "noroot.mm.json"
        path.write_text(json.dumps({"title": "x"}), encoding="utf-8")
        with self.assertRaises(RepositoryError):
            self.repo.load(path)

    def test_exists(self):
        path = self.dir / "m.mm.json"
        self.assertFalse(self.repo.exists(path))
        self.repo.save(_sample(), path)
        self.assertTrue(self.repo.exists(path))


class TestRepositoryProtocol(unittest.TestCase):
    def test_json_repo_satisfies_protocol(self):
        # Structural typing: JsonFileRepository has the right methods.
        self.assertIsInstance(JsonFileRepository(), MindMapRepository)


if __name__ == "__main__":
    unittest.main()
