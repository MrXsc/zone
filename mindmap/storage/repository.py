"""Repository abstraction for MindMap persistence.

Using typing.Protocol (runtime_checkable) keeps this layer decoupled:
implementations need not inherit anything — structural typing means any
object with the right methods satisfies the interface. This is the seam
along which SQLite/YAML/HTTP backends will later plug in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from mindmap.domain.mindmap import MindMap


class RepositoryError(Exception):
    """Base error for storage problems (missing file, corrupt data, ...)."""


@runtime_checkable
class MindMapRepository(Protocol):
    """Interface for reading and writing MindMap documents.

    Paths are Path objects so callers stay backend-agnostic: a file
    backend treats them as filesystem locations; a future key-value
    backend might treat the stem as a key.
    """

    def load(self, path: Path) -> MindMap:
        """Load a MindMap from ``path``. Raise RepositoryError on failure."""
        ...

    def save(self, mindmap: MindMap, path: Path) -> None:
        """Persist ``mindmap`` to ``path``. Raise RepositoryError on failure."""
        ...

    def exists(self, path: Path) -> bool:
        """Return True if a document exists at ``path``."""
        ...
