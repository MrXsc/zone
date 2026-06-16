"""CLI — the thinnest possible presentation surface.

Subcommands map 1:1 to service use cases. The CLI knows NOTHING about
JSON, layout math, or SVG details — it only converts argv <-> service
calls and prints results. That keeps it tiny and keeps all real logic
testable without parsing argv.

Usage:
    mm new "Title" --root "Center" -o map.mm.json
    mm open map.mm.json
    mm to-md map.mm.json [-o out.md]
    mm from-md in.md -o map.mm.json
    mm render map.mm.json [-o diag.svg]

Outputs default to stdout when -o is omitted (except render, which writes
<stem>.svg beside the source by default since SVG on stdout is awkward).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mindmap.application.services import MindMapService
from mindmap.storage.json_repository import JsonFileRepository


# --------------------------------------------------------------------------- #
#  entry point
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    service = MindMapService(repository=JsonFileRepository())

    try:
        return args.func(service, args)
    except FileNotFoundError as exc:
        return _fail(f"File not found: {exc.filename or exc}")
    except ValueError as exc:
        return _fail(f"Invalid input: {exc}")
    except Exception as exc:  # noqa: BLE001 — CLI is the boundary
        return _fail(f"Error: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mm",
        description="A minimal, lightweight mind-mapping tool.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # new --------------------------------------------------------------------
    p_new = sub.add_parser("new", help="Create a new mind map.")
    p_new.add_argument("title", help="Document title.")
    p_new.add_argument("--root", default="中心主题",
                       help="Root node text (default: '中心主题').")
    p_new.add_argument("-o", "--output", help="Output .mm.json path.")
    p_new.set_defaults(func=_cmd_new)

    # open -------------------------------------------------------------------
    p_open = sub.add_parser("open", help="Open and print a mind map tree.")
    p_open.add_argument("path", help="Path to a .mm.json file.")
    p_open.set_defaults(func=_cmd_open)

    # to-md ------------------------------------------------------------------
    p_tomd = sub.add_parser("to-md", help="Export a mind map to Markdown.")
    p_tomd.add_argument("path", help="Path to a .mm.json file.")
    p_tomd.add_argument("-o", "--output", help="Output .md path.")
    p_tomd.set_defaults(func=_cmd_to_md)

    # from-md ----------------------------------------------------------------
    p_frommd = sub.add_parser("from-md", help="Import a mind map from Markdown.")
    p_frommd.add_argument("path", help="Path to a .md file.")
    p_frommd.add_argument("-o", "--output", required=True,
                          help="Output .mm.json path.")
    p_frommd.set_defaults(func=_cmd_from_md)

    # render -----------------------------------------------------------------
    p_render = sub.add_parser("render", help="Render a mind map to SVG.")
    p_render.add_argument("path", help="Path to a .mm.json file.")
    p_render.add_argument("-o", "--output", help="Output .svg path.")
    p_render.set_defaults(func=_cmd_render)

    return parser


# --------------------------------------------------------------------------- #
#  command handlers
# --------------------------------------------------------------------------- #

def _cmd_new(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.new(title=args.title, root_text=args.root)
    out = args.output or _default_name(args.title, suffix=".mm.json")
    written = service.save_as(mm, out)
    print(f"Created {written} ({mm.count()} node(s)).")
    return 0


def _cmd_open(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.path)
    print(f"Title: {mm.title}")
    print(f"Nodes: {mm.count()}")
    print(_ascii_tree(mm))
    return 0


def _cmd_to_md(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.path)
    md = service.export_markdown(mm)
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Wrote {args.output}.")
    else:
        sys.stdout.write(md)
    return 0


def _cmd_from_md(service: MindMapService, args: argparse.Namespace) -> int:
    text = Path(args.path).read_text(encoding="utf-8")
    mm = service.import_markdown(text)
    service.save_as(mm, args.output)
    print(f"Imported {mm.count()} node(s) -> {args.output}.")
    return 0


def _cmd_render(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.path)
    svg = service.render_svg(mm)
    out = args.output or (Path(args.path).with_suffix(".svg"))
    Path(out).write_text(svg, encoding="utf-8")
    print(f"Rendered {mm.count()} node(s) -> {out}.")
    return 0


# --------------------------------------------------------------------------- #
#  small view helpers
# --------------------------------------------------------------------------- #

def _ascii_tree(mm) -> str:
    """Render a quick text outline of the tree for `open`."""
    from mindmap.domain.node import Node  # local: keeps CLI top clean
    lines: list[str] = []

    def walk(node: Node, prefix: str, is_last: bool, is_root: bool) -> None:
        if is_root:
            lines.append(node.text or "(empty)")
            child_prefix = ""
        else:
            connector = "└─ " if is_last else "├─ "
            lines.append(f"{prefix}{connector}{node.text}")
            child_prefix = prefix + ("   " if is_last else "│  ")
        kids = node.children
        for i, child in enumerate(kids):
            walk(child, child_prefix, i == len(kids) - 1, is_root=False)

    walk(mm.root, "", is_last=True, is_root=True)
    return "\n".join(lines)


def _default_name(title: str, *, suffix: str) -> str:
    """Turn a title into a safe filename with ``suffix``."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title.strip())
    safe = safe.strip("_") or "mindmap"
    return f"{safe}{suffix}"


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
