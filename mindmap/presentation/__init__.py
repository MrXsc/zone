"""Presentation layer — user-facing entry points.

The skeleton ships a CLI. A future Web UI or desktop GUI would be a
sibling here; the application service gives all of them the same API.

Dependencies: application only (it talks to the service, never to inner
layers directly).

Note: we deliberately do NOT import `main` here. Pre-importing the CLI
module triggers a runpy warning under ``python -m mindmap.presentation.cli``
because the package __init__ loads the module before runpy runs it. Import
it lazily where needed, or use the package-level entry point in
``mindmap.__main__``.
"""
