"""Convert layer — bidirectional, lossy format exchange.

Markdown is the human-friendly exchange format. It uses indented
bullet lists to encode the tree. Round-tripping through Markdown is
intentionally LOSSY: ids and notes are dropped (Markdown has nowhere
to put them). Use .mm.json for lossless round-trips.

Dependencies: domain only.
"""

from mindmap.convert.markdown import to_markdown, from_markdown

__all__ = ["to_markdown", "from_markdown"]
