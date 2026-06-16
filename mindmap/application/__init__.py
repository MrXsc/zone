"""Application layer — use-case orchestration.

This layer re-exports the service class from the presentation layer
for backward compatibility with tests and external consumers.
"""

from mindmap.presentation.cli import MindMapService

__all__ = ["MindMapService"]
