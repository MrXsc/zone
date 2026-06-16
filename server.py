"""Flask server — serves the Web UI and mindmap API.

Usage:
    python server.py [--port 5000] [--dir .]

Opens the UI at http://localhost:5000.
Optional ?path= query param loads a specific .mm.json file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from mindmap.domain.mindmap import MindMap
from mindmap.layout import layout as compute_layout
from mindmap.rendering.svg import render_svg
from mindmap.storage.json_repository import JsonFileRepository

app = Flask(__name__, static_folder=None)
WORK_DIR = Path.cwd()
REPO = JsonFileRepository()


# ── helpers ─────────────────────────────────────

def _resolve_path(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = WORK_DIR / p
    return p.resolve()


def _load_mm(raw_path: str) -> MindMap:
    return REPO.load(_resolve_path(raw_path))


def _boxes_dict(mm: MindMap) -> dict:
    """Compute layout and return {node_id: {x,y,width,height}, ...}."""
    from mindmap.layout import layout as compute_layout  # already imported
    boxes = compute_layout(mm)
    return {
        nid: {"x": b.x, "y": b.y, "width": b.width, "height": b.height}
        for nid, b in boxes.items()
    }


def _mutate(data: dict, mutator):
    """Deserialize → mutate → relayout → return {mindmap, boxes}."""
    mm = MindMap.from_dict(data["mindmap"])
    mutator(mm)
    mm.touch()
    return {"mindmap": mm.to_dict(), "boxes": _boxes_dict(mm)}


# ── API ─────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(_HERE / "mindmap" / "ui", "index.html")


@app.route("/api/map", methods=["GET"])
def api_map_get():
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "Missing ?path="}), 400
    try:
        return jsonify(_load_mm(path).to_dict())
    except FileNotFoundError:
        return jsonify({"error": f"Not found: {path}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/map", methods=["PUT"])
def api_map_put():
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "Missing ?path="}), 400
    try:
        mm = MindMap.from_dict(request.get_json(force=True))
        REPO.save(mm, _resolve_path(path))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/layout", methods=["POST"])
def api_layout():
    try:
        mm = MindMap.from_dict(request.get_json(force=True))
        boxes = compute_layout(mm)
        result = {
            nid: {"x": b.x, "y": b.y, "width": b.width, "height": b.height}
            for nid, b in boxes.items()
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/render", methods=["POST"])
def api_render():
    try:
        data = request.get_json(force=True)
        mm = MindMap.from_dict(data)
        boxes = compute_layout(mm)
        svg = render_svg(mm, boxes, style_map=mm.styles)
        return jsonify({"svg": svg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── edit API ────────────────────────────────────

@app.route("/api/node/add-child", methods=["POST"])
def api_node_add_child():
    try:
        body = request.get_json(force=True)
        return jsonify(_mutate(body, lambda mm: mm.add_child(
            body["parent_id"], body["text"],
            note=body.get("note"),
            index=body.get("index"),
        )))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/add-sibling", methods=["POST"])
def api_node_add_sibling():
    try:
        body = request.get_json(force=True)
        node_id = body["node_id"]
        text = body["text"]
        before = body.get("before", False)

        def _do(mm):
            parent = mm.find_parent(node_id)
            if parent is None:
                raise ValueError("Cannot add sibling to root node")
            siblings = parent.children
            idx = next(i for i, c in enumerate(siblings) if c.id == node_id)
            insert_at = idx if before else idx + 1
            mm.add_child(parent.id, text, index=insert_at)

        return jsonify(_mutate(body, _do))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/add-parent", methods=["POST"])
def api_node_add_parent():
    try:
        body = request.get_json(force=True)
        node_id = body["node_id"]
        text = body["text"]

        def _do(mm):
            from mindmap.domain.node import Node
            child = mm.find(node_id)
            if child is None:
                raise ValueError(f"Node not found: {node_id}")
            parent = mm.find_parent(node_id)
            if parent is None:
                raise ValueError("Cannot add parent to root node")
            new_parent = Node.create(text)
            idx = next(i for i, c in enumerate(parent.children) if c.id == node_id)
            parent.children[idx] = new_parent
            new_parent.add_child(child)

        return jsonify(_mutate(body, _do))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/update", methods=["POST"])
def api_node_update():
    try:
        body = request.get_json(force=True)
        return jsonify(_mutate(body, lambda mm: mm.update_node(
            body["node_id"],
            text=body.get("text"),
            note=body.get("note"),
        )))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/delete", methods=["POST"])
def api_node_delete():
    try:
        body = request.get_json(force=True)
        return jsonify(_mutate(body, lambda mm: mm.remove(body["node_id"])))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/move", methods=["POST"])
def api_node_move():
    try:
        body = request.get_json(force=True)
        return jsonify(_mutate(body, lambda mm: mm.move(
            body["node_id"], body["to_parent_id"],
            index=body.get("index"),
        )))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/node/reorder", methods=["POST"])
def api_node_reorder():
    try:
        body = request.get_json(force=True)
        direction = body["direction"]  # "up" or "down"

        def _do(mm):
            node_id = body["node_id"]
            parent = mm.find_parent(node_id)
            if parent is None:
                raise ValueError("Cannot reorder root node")
            siblings = parent.children
            idx = next(i for i, c in enumerate(siblings) if c.id == node_id)
            if direction == "up" and idx > 0:
                siblings[idx], siblings[idx - 1] = siblings[idx - 1], siblings[idx]
            elif direction == "down" and idx < len(siblings) - 1:
                siblings[idx], siblings[idx + 1] = siblings[idx + 1], siblings[idx]

        return jsonify(_mutate(body, _do))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── static files ────────────────────────────────

@app.route("/<path:filename>")
def static_files(filename):
    ui = _HERE / "mindmap" / "ui"
    if (ui / filename).is_file():
        return send_from_directory(ui, filename)
    return send_from_directory(_HERE, filename)


# ── entry ────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="mindmap Web UI")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--dir", default=str(Path.cwd()))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    global WORK_DIR
    WORK_DIR = Path(args.dir).resolve()
    print(f"[mindmap] UI  --  http://localhost:{args.port}")
    print(f"  Working dir: {WORK_DIR}")
    print(f"  Open: http://localhost:{args.port}/?path=examples/os_demo.mm.json")
    app.run(port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
