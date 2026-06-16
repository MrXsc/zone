"""Domain layer — core data model. Zero dependencies.

This package must not import from any other mindmap layer. It holds the
pure tree structure (Node, MindMap) and the operations that are intrinsic
to that structure.
"""

from mindmap.domain.node import Node
from mindmap.domain.mindmap import MindMap

__all__ = ["Node", "MindMap"]
