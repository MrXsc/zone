"""MindMap — a named tree with metadata.

MindMap is the aggregate root: it owns a single root Node plus
document-level metadata (title, timestamps). It delegates tree operations
to the root node while keeping the document concerns here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from mindmap.domain.node import Node, _new_id
from mindmap.domain.style import NodeStyle, StyleMap


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
    styles: StyleMap | None = None

    # NOTE: no __post_init__ here. The field defaults already stamp a freshly
    # constructed document; touching in __post_init__ would overwrite the
    # preserved timestamps when reconstructing a loaded document, breaking
    # lossless round-trips. Use .new() to create, .touch() to mark edits.

    # ---- M3 editing mutators (need parent access) ---------------------------

    def add_child(self, parent_id: str, text: str, *,
                  note: str | None = None,
                  index: int | None = None) -> "Node":
        """Create a new child under *parent_id* and return it.

        Raises ValueError if *parent_id* is not found.
        """
        parent = self.find(parent_id)
        if parent is None:
            raise ValueError(f"Node not found: {parent_id}")
        child = Node.create(text, note=note)
        parent.add_child(child, index=index)
        return child

    def update_node(self, node_id: str, *,
                    text: str | None = None,
                    note: str | None = None) -> "Node":
        """Set one or more fields on *node_id*.

        ``None`` for a field means "don't change it".  Pass an explicit
        value (including ``None`` for *note*) to clear.
        """
        node = self.find(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")
        if text is not None:
            node.text = text
        if note is not None:
            node.note = note if note else None
        return node

    def remove(self, node_id: str) -> "Node | None":
        """Remove the subtree rooted at *node_id*.

        Rejects deleting the root.  Returns the detached subtree (or
        ``None`` when *node_id* is not found — idempotent).
        """
        if node_id == self.root.id:
            raise ValueError("Cannot remove the root node")
        parent = self.find_parent(node_id)
        if parent is None:
            return None          # node not present at all
        return parent.remove_child(node_id)

    def move(self, node_id: str, to_parent_id: str, *,
             index: int | None = None) -> "Node":
        """Detach *node_id* and attach it under *to_parent_id*.

        Raises ValueError when:
        - either id is not found,
        - *to_parent_id* is the same as *node_id* (self-loop),
        - *to_parent_id* is a descendant of *node_id* (cycle),
        - *node_id* is the root.
        """
        if node_id == self.root.id:
            raise ValueError("Cannot move the root node")
        node = self.find(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")
        new_parent = self.find(to_parent_id)
        if new_parent is None:
            raise ValueError(f"Target parent not found: {to_parent_id}")
        if node_id == to_parent_id:
            raise ValueError("Cannot move a node to itself")
        # Cycle check: is the target parent inside the moved subtree?
        if node.find(to_parent_id) is not None:
            raise ValueError("Cannot move a node to its own descendant")

        old_parent = self.find_parent(node_id)
        if old_parent is not None:
            old_parent.remove_child(node_id)
        new_parent.add_child(node, index=index)
        return node

    # ---- M4 style helpers --------------------------------------------------

    def set_style(self, node_id: str, **fields) -> None:
        """Create or update a :class:`NodeStyle` for *node_id*.

        Accepted keyword arguments match :class:`~mindmap.domain.style.NodeStyle`
        fields (fill, stroke, text_color, font_size, font_weight, border_radius).
        """
        if self.styles is None:
            self.styles = StyleMap()
        existing = self.styles.get(node_id) or NodeStyle()
        merged = NodeStyle(
            **{f: fields.get(f, getattr(existing, f))
               for f in NodeStyle.__dataclass_fields__}
        )
        self.styles.set(node_id, merged)

    def clear_style(self, node_id: str) -> None:
        """Remove the per-node style for *node_id*."""
        if self.styles is not None:
            self.styles.remove(node_id)
            if not self.styles.styles:
                self.styles = None   # keep serialization clean

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
        d = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root": self.root.to_dict(),
        }
        if self.styles is not None and self.styles.styles:
            d["styles"] = self.styles.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MindMap":
        mm = cls(
            id=data.get("id") or _new_id(),
            title=data.get("title", ""),
            created_at=data.get("created_at") or _utcnow_iso(),
            updated_at=data.get("updated_at") or _utcnow_iso(),
            root=Node.from_dict(data.get("root") or {}),
        )
        raw_styles = data.get("styles")
        if raw_styles:
            mm.styles = StyleMap.from_dict(raw_styles)
        return mm
