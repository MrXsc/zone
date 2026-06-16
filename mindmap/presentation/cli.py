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

    # --- M3 editing ---------------------------------------------------------
    _DOC_HELP = "Path to the .mm.json document (default: mindmap.mm.json)."

    # add
    p_add = sub.add_parser("add", help="Add a child node.")
    p_add.add_argument("parent_id", help="Id of the parent node.")
    p_add.add_argument("text", help="Text for the new node.")
    p_add.add_argument("--note", help="Optional note.")
    p_add.add_argument("--index", type=int, help="Insert at 0-based index.")
    p_add.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_add.set_defaults(func=_cmd_add)

    # edit
    p_edit = sub.add_parser("edit", help="Update a node's text or note.")
    p_edit.add_argument("node_id", help="Id of the node to edit.")
    p_edit.add_argument("--text", help="New text (omit to keep current).")
    p_edit.add_argument("--note", help="New note (omit to keep current).")
    p_edit.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_edit.set_defaults(func=_cmd_edit)

    # rm
    p_rm = sub.add_parser("rm", help="Remove a subtree.")
    p_rm.add_argument("node_id", help="Id of the node to remove.")
    p_rm.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_rm.set_defaults(func=_cmd_rm)

    # move
    p_move = sub.add_parser("move", help="Move a subtree under another parent.")
    p_move.add_argument("node_id", help="Id of the node to move.")
    p_move.add_argument("--to", required=True, dest="to_parent_id",
                        help="Target parent id.")
    p_move.add_argument("--index", type=int, help="Insert at 0-based index.")
    p_move.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_move.set_defaults(func=_cmd_move)

    # ls
    p_ls = sub.add_parser("ls", help="List all nodes (id + text).")
    p_ls.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_ls.set_defaults(func=_cmd_ls)

    # --- M4 style -----------------------------------------------------------

    # style
    p_style = sub.add_parser(
        "style", help="Set per-node style overrides.")
    p_style.add_argument("node_id", help="Id of the node to style.")
    p_style.add_argument("--fill", help="Fill color (e.g. '#ff0').")
    p_style.add_argument("--stroke", help="Stroke color.")
    p_style.add_argument("--text-color", dest="text_color",
                         help="Text color.")
    p_style.add_argument("--font-size", type=float, dest="font_size",
                         help="Font size in px.")
    p_style.add_argument("--font-weight", dest="font_weight",
                         help="Font weight (e.g. 'bold', '600').")
    p_style.add_argument("--border-radius", type=float,
                         dest="border_radius",
                         help="Border radius in px.")
    p_style.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_style.set_defaults(func=_cmd_style)

    # unstyle
    p_unstyle = sub.add_parser(
        "unstyle", help="Remove per-node style overrides.")
    p_unstyle.add_argument("node_id", help="Id of the node to unstyle.")
    p_unstyle.add_argument("--doc", default="mindmap.mm.json", help=_DOC_HELP)
    p_unstyle.set_defaults(func=_cmd_unstyle)

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
#  M3 editing command handlers
# --------------------------------------------------------------------------- #

def _cmd_add(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    node = service.add_child(mm, args.parent_id, args.text,
                              note=args.note, index=args.index)
    service.save_as(mm, args.doc)
    print(f"Added {node.id} ({node.text}) under {args.parent_id}.")
    return 0


def _cmd_edit(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    node = service.update_node(mm, args.node_id,
                                text=args.text, note=args.note)
    service.save_as(mm, args.doc)
    print(f"Updated {args.node_id} -> text={node.text!r} note={node.note!r}.")
    return 0


def _cmd_rm(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    subtree = service.remove(mm, args.node_id)
    if subtree is None:
        return _fail(f"Node not found: {args.node_id}")
    service.save_as(mm, args.doc)
    print(f"Removed {args.node_id} ({subtree.count()} node(s)).")
    return 0


def _cmd_move(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    node = service.move(mm, args.node_id, args.to_parent_id,
                         index=args.index)
    service.save_as(mm, args.doc)
    print(f"Moved {args.node_id} under {args.to_parent_id}.")
    return 0


def _cmd_ls(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    for node in mm.walk():
        suffix = f"  # {node.note}" if node.note else ""
        print(f"  {node.id}  {node.text}{suffix}")
    print(f"Total: {mm.count()} node(s).")
    return 0


# --------------------------------------------------------------------------- #
#  M4 style command handlers
# --------------------------------------------------------------------------- #

def _cmd_style(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    # Collect only the fields that were explicitly passed (non-None).
    fields = {k: v for k, v in {
        "fill": args.fill,
        "stroke": args.stroke,
        "text_color": args.text_color,
        "font_size": args.font_size,
        "font_weight": args.font_weight,
        "border_radius": args.border_radius,
    }.items() if v is not None}
    if not fields:
        return _fail("No style fields specified. "
                     "Use --fill, --stroke, --text-color, etc.")
    service.set_style(mm, args.node_id, **fields)
    service.save_as(mm, args.doc)
    print(f"Styled {args.node_id}: {fields}")
    return 0


def _cmd_unstyle(service: MindMapService, args: argparse.Namespace) -> int:
    mm = service.open(args.doc)
    service.clear_style(mm, args.node_id)
    service.save_as(mm, args.doc)
    print(f"Cleared style for {args.node_id}.")
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
