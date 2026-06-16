"""Node — the atomic unit of a mind map.

A Node is a plain tree node: it holds text, an optional note, and a list
of children. It deliberately stores NO parent reference. Trees with
parent back-pointers are painful to (de)serialize and easy to corrupt;
when a parent is needed, callers obtain it via MindMap.find_parent().

Styling (color, font, icon, ...) is intentionally absent from the
skeleton — it will live behind a separate interface later, so the core
model stays minimal.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def _new_id() -> str:
    """Return a fresh hex id. Centralized so ids are easy to retemplate."""
    return uuid.uuid4().hex


@dataclass
class Node:
    """A single node in the mind-map tree.

    Attributes:
        id:       Stable hex id (uuid4). Preserved across saves; regenerated
                  only when importing from lossy formats (e.g. Markdown).
        text:     Primary label shown on the node. May be empty.
        note:     Optional longer note attached to the node. Not rendered in
                  the skeleton; kept on the model so future layers can use it.
        children: Ordered child nodes. A node with no children is a leaf.
    """

    text: str = ""
    note: str | None = None
    id: str = field(default_factory=_new_id)
    children: list["Node"] = field(default_factory=list)

    # ---- in-place mutators (M3) ----------------------------------------------

    def set_text(self, text: str) -> "Node":
        """Change this node's text and return self."""
        self.text = text
        return self

    def update_note(self, note: str | None) -> "Node":
        """Change this node's note and return self (``None`` clears it)."""
        self.note = note
        return self

    def remove_child(self, child: "Node | str") -> "Node | None":
        """Detach *child* (by object or id) and return it.

        The removed subtree is returned so callers can inspect or re-attach
        it elsewhere. Returns ``None`` when *child* is not among immediate
        children (not a descendant search — use :meth:`find` first).
        """
        child_id = child.id if isinstance(child, Node) else child
        for i, c in enumerate(self.children):
            if c.id == child_id:
                return self.children.pop(i)
        return None

    def reorder_children(self, order: list[str]) -> None:
        """Reorder immediate children to match *order* (a list of ids).

        Raises ValueError if *order* contains duplicate, missing, or
        unknown ids.
        """
        if len(order) != len(set(order)):
            raise ValueError("Duplicate ids in order list")
        if len(order) != len(self.children):
            raise ValueError(
                f"order has {len(order)} ids but node has "
                f"{len(self.children)} children"
            )
        id_to_child = {c.id: c for c in self.children}
        missing = [oid for oid in order if oid not in id_to_child]
        if missing:
            raise ValueError(f"Unknown child id(s): {missing}")
        self.children = [id_to_child[oid] for oid in order]

    def index_of(self, child: "Node | str") -> int:
        """Return the 0-based index of *child* (by object or id).

        Raises ValueError if *child* is not an immediate child.
        """
        child_id = child.id if isinstance(child, Node) else child
        for i, c in enumerate(self.children):
            if c.id == child_id:
                return i
        raise ValueError(f"Node {child_id} is not a child of {self.id}")

    # ---- construction helpers ------------------------------------------------

    @classmethod
    def create(cls, text: str, *, note: str | None = None) -> "Node":
        """Create a fresh node with a new id."""
        return cls(text=text, note=note)

    def add_child(self, child: "Node", *, index: int | None = None) -> "Node":
        """Append (or insert at ``index``) a child and return it."""
        if index is None:
            self.children.append(child)
        else:
            self.children.insert(index, child)
        return child

    # ---- traversal -----------------------------------------------------------

    def walk(self):
        """Yield this node then all descendants in depth-first pre-order."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, node_id: str) -> "Node | None":
        """Return the descendant with ``node_id``, or None."""
        for node in self.walk():
            if node.id == node_id:
                return node
        return None

    def find_parent(self, node_id: str) -> "Node | None":
        """Return the parent of ``node_id`` within this subtree, or None.

        Returns None if the node is the root itself or is not present.
        """
        for node in self.walk():
            for child in node.children:
                if child.id == node_id:
                    return node
        return None

    # ---- queries -------------------------------------------------------------

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def count(self) -> int:
        """Total node count in this subtree (including self)."""
        return sum(1 for _ in self.walk())

    # ---- serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "note": self.note,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        return cls(
            id=data.get("id") or _new_id(),
            text=data.get("text", ""),
            note=data.get("note"),
            children=[cls.from_dict(c) for c in data.get("children", [])],
        )

    def clone(self) -> "Node":
        """Deep copy with fresh ids (e.g. for templating).

        All nodes in the subtree get new ids, recursively.
        """
        return _clone_node(self)


def _clone_node(node: "Node") -> "Node":
    """Recursive helper: copy structure and text/note, regenerate ids."""
    return Node(
        id=_new_id(),
        text=node.text,
        note=node.note,
        children=[_clone_node(c) for c in node.children],
    )
