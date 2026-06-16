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
