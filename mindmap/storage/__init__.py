"""Storage layer — persistence behind a Repository abstraction.

The domain model knows nothing about files, JSON, or databases. This
layer defines a ``MindMapRepository`` Protocol and ships one concrete
implementation (JsonFileRepository). Swapping in SQLite/YAML/HTTP later
means adding a new implementation here — nothing upstream changes.

Dependencies: domain only.
"""

from mindmap.storage.repository import MindMapRepository, RepositoryError
from mindmap.storage.json_repository import JsonFileRepository

__all__ = ["MindMapRepository", "RepositoryError", "JsonFileRepository"]
