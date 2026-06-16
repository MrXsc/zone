"""JSON file repository — the default, dependency-free persistence.

Native format is ``.mm.json``: the MindMap serialized verbatim via
domain.to_dict/from_dict. This is the only format that round-trips
without loss (preserves ids, notes, timestamps). Markdown is the lossy
exchange format handled in convert/.

Design notes:
- Atomic writes: write to a temp file in the same dir, then os.replace,
  so a crash mid-write never produces a truncated document.
- UTF-8 everywhere; ensure_ascii=False keeps CJK text readable in the
  raw file (helps git diffs and manual editing).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from mindmap.domain.mindmap import MindMap
from mindmap.storage.repository import RepositoryError

# Suffix that marks the native, lossless format.
NATIVE_SUFFIX = ".mm.json"


class JsonFileRepository:
    """Read/write MindMap documents as .mm.json files."""

    def load(self, path: Path) -> MindMap:
        path = Path(path)
        if not path.exists():
            raise RepositoryError(f"File not found: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryError(f"Failed to read {path}: {exc}") from exc

        if not isinstance(data, dict) or "root" not in data:
            raise RepositoryError(f"Invalid mind-map document: {path}")
        try:
            return MindMap.from_dict(data)
        except Exception as exc:  # malformed structure
            raise RepositoryError(f"Corrupt document {path}: {exc}") from exc

    def save(self, mindmap: MindMap, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(mindmap.to_dict(), ensure_ascii=False,
                             indent=2)

        # Atomic replace: build a temp file in the SAME directory so the
        # final os.replace is a single atomic rename on the same volume.
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".tmp",
                dir=str(path.parent), delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp_name = tmp.name
            os.replace(tmp_name, path)
        except OSError as exc:
            # Clean up the orphaned temp file on failure.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise RepositoryError(f"Failed to write {path}: {exc}") from exc

    def exists(self, path: Path) -> bool:
        return Path(path).exists()
