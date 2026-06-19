"""End-to-end tests for the application service and CLI."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mindmap.presentation.cli import MindMapService
from mindmap.domain.node import Node
from mindmap.presentation.cli import main
from mindmap.storage.json_repository import JsonFileRepository


class TestService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.svc = MindMapService(JsonFileRepository())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_open_roundtrip(self):
        mm = self.svc.new("T", "root")
        path = self.dir / "m.mm.json"
        self.svc.save_as(mm, path)
        loaded = self.svc.open(path)
        self.assertEqual(loaded.to_dict(), mm.to_dict())

    def test_markdown_export_import_roundtrip(self):
        mm = self.svc.new("T", "root")
        mm.root.add_child(Node.create("a"))
        md = self.svc.export_markdown(mm)
        restored = self.svc.import_markdown(md)
        self.assertEqual(restored.root.text, "root")
        self.assertEqual(restored.root.children[0].text, "a")

    def test_render_svg_returns_document(self):
        mm = self.svc.new("T", "root")
        mm.root.add_child(Node.create("a"))
        svg = self.svc.render_svg(mm)
        self.assertIn("<svg", svg)


class TestCliEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_full_pipeline(self):
        mm_path = self.dir / "m.mm.json"
        md_path = self.dir / "out.md"
        svg_path = self.dir / "m.svg"

        # new
        rc = main(["new", "Pipeline", "--root", "核心", "-o", str(mm_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(mm_path.exists())

        # open
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["open", str(mm_path)])
        self.assertEqual(rc, 0)
        self.assertIn("核心", buf.getvalue())

        # to-md
        rc = main(["to-md", str(mm_path), "-o", str(md_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(md_path.exists())
        self.assertIn("核心", md_path.read_text(encoding="utf-8"))

        # from-md (roundtrip via markdown)
        rc = main(["from-md", str(md_path), "-o", str(self.dir / "imp.mm.json")])
        self.assertEqual(rc, 0)
        self.assertTrue((self.dir / "imp.mm.json").exists())

        # render
        rc = main(["render", str(mm_path), "-o", str(svg_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(svg_path.exists())
        self.assertIn("<svg", svg_path.read_text(encoding="utf-8"))

    def test_missing_file_returns_error(self):
        rc = main(["open", str(self.dir / "nope.mm.json")])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
