"""MindMap — a named tree with metadata.

MindMap is the aggregate root: it owns a single root Node plus
document-level metadata (title, timestamps). It delegates tree operations
to the root node while keeping the document concerns here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from mindmap.domain.node import Node, _new_id


def _utcnow_iso() -> str:
    """Current time as an ISO-8601 UTC string. Centralized for testability."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MindMap:
    """The full mind-map document.

    Attributes:
        title:      Human-readable document title.
        root:       The root Node of the tree.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-modified timestamp.
        id:         Stable document id (uuid4 hex).
    """

    title: str
    root: Node
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)
    id: str = field(default_factory=_new_id)

    # NOTE: no __post_init__ here. The field defaults already stamp a freshly
    # constructed document; touching in __post_init__ would overwrite the
    # preserved timestamps when reconstructing a loaded document, breaking
    # lossless round-trips. Use .new() to create, .touch() to mark edits.

    # ---- lifecycle -----------------------------------------------------------

    @classmethod
    def new(cls, title: str, root_text: str, *, note: str | None = None) -> "MindMap":
        """Create a fresh mind map with a single root node."""
        return cls(title=title, root=Node.create(root_text, note=note))

    def touch(self) -> None:
        """Mark the document as modified now."""
        self.updated_at = _utcnow_iso()

    # ---- delegation to root --------------------------------------------------

    def walk(self):
        yield from self.root.walk()

    def find(self, node_id: str) -> Node | None:
        return self.root.find(node_id)

    def find_parent(self, node_id: str) -> Node | None:
        return self.root.find_parent(node_id)

    def count(self) -> int:
        return self.root.count()

    # ---- serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root": self.root.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MindMap":
        return cls(
            id=data.get("id") or _new_id(),
            title=data.get("title", ""),
            created_at=data.get("created_at") or _utcnow_iso(),
            updated_at=data.get("updated_at") or _utcnow_iso(),
            root=Node.from_dict(data.get("root") or {}),
        )
