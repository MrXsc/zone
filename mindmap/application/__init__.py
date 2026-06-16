"""Application layer — use-case orchestration.

This layer wires the inner layers together into the operations a user or
UI actually wants: create a map, open/save it, convert to/from Markdown,
render to SVG. It holds the repository and knows which layout/renderer to
call, so the presentation layer (CLI or a future UI) stays trivial.

It is the ONLY layer that knows about multiple inner layers at once; it
depends on domain, storage, convert, layout, rendering.

Dependencies: domain, storage, convert, layout, rendering.
"""

from mindmap.application.services import MindMapService

__all__ = ["MindMapService"]
