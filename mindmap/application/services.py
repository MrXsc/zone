"""MindMapService — the use cases of the application.

Each method is one user-facing operation. The service takes dependencies
through its constructor (dependency injection): pass any MindMapRepository
to swap persistence. The layout options can also be injected, which lets
a future UI expose layout knobs without touching the CLI.

Keeping this layer thin and side-effect-light (file I/O happens via the
repository, rendering returns strings) makes the operations easy to test
and easy to call from any presentation surface.
"""

from __future__ import annotations

from pathlib import Path

from mindmap.convert.markdown import from_markdown, to_markdown
from mindmap.domain.mindmap import MindMap
from mindmap.layout import LayoutOptions, layout
from mindmap.rendering.svg import render_svg
from mindmap.storage.repository import MindMapRepository


class MindMapService:
    """Orchestrates domain/storage/convert/layout/rendering into use cases.

    Args:
        repository:  persistence backend (default JsonFileRepository).
        layout_opts: layout options; None uses the balanced-tree defaults.
    """

    def __init__(self, repository: MindMapRepository,
                 layout_opts: LayoutOptions | None = None) -> None:
        self._repo = repository
        self._layout_opts = layout_opts

    # --- document lifecycle --------------------------------------------------

    def new(self, title: str, root_text: str) -> MindMap:
        """Create an in-memory mind map (not yet persisted)."""
        return MindMap.new(title=title, root_text=root_text)

    def open(self, path: str | Path) -> MindMap:
        """Load a mind map from the repository."""
        return self._repo.load(Path(path))

    def save_as(self, mindmap: MindMap, path: str | Path) -> Path:
        """Persist ``mindmap`` to ``path``; returns the path written."""
        mindmap.touch()
        target = Path(path)
        self._repo.save(mindmap, target)
        return target

    # --- Markdown exchange (lossy) ------------------------------------------

    def export_markdown(self, mindmap: MindMap) -> str:
        return to_markdown(mindmap)

    def import_markdown(self, text: str, *, title: str | None = None) -> MindMap:
        return from_markdown(text, title=title)

    # --- visualization -------------------------------------------------------

    def render_svg(self, mindmap: MindMap) -> str:
        """Layout + render to an SVG string using the configured options."""
        boxes = layout(mindmap, self._layout_opts)
        return render_svg(mindmap, boxes)
