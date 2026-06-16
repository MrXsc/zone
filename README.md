<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/dependencies-zero-success" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/stdlib-only-important" alt="Stdlib Only">
</p>

<h1 align="center">🧠Zone Mindmap</h1>

<p align="center">
  <em>A minimal, elegant, zero-dependency mind-mapping tool for the command line.</em><br>
  Create, edit, style, and render mind maps — all with Python's standard library.
</p>

---

## ✨ Features

- **📦 Zero dependencies** — pure Python stdlib. `pip install` nothing.
- **🌳 Tree data model** — rooted, ordered, walkable tree with UUID-stable nodes.
- **✏️ Full node editing** — add, edit, remove, move, reorder — all from the CLI.
- **🎨 Per-node style overrides** — independent fill / stroke / text color / font size / font weight / border radius per node.
- **📐 Auto-balanced layout** — left/right tree layout that maximizes screen space.
- **🖼️ SVG export** — polished vector output with themes, bezier connectors, and rounded cards.
- **🔁 Markdown round-trip** — import/export indented Markdown lists (lossy, great for sharing).
- **💾 JSON persistence** — human-readable `.mm.json` format with atomic saves.
- **🧩 Layered architecture** — core domain has zero dependencies; swap storage, add a UI, or build a web app without touching the model.

## 📸 Demo

```
                 ┌── 进程与线程
     ┌── 进程管理 ── 调度算法
     │    (红)     ├── 同步互斥
     │             └── IPC 通信
     ├── 内存管理 ── 分页分段
     │    (蓝)     ├── 虚拟内存
     │             └── 页面置换
操作系统─── 文件系统 ── 目录结构
     │    (绿)     ├── 文件分配
     │             └── 磁盘管理
     ├── 设备管理 ── I/O 控制
     │    (橙)     ├── 缓冲技术
     │             └── SPOOLing
     └── 死锁 ──── 必要条件
          (紫)     ├── 处理方法
                   └── 银行家算法
```

> Example output: [`examples/os_demo.svg`](examples/os_demo.svg) · [`examples/demo.svg`](examples/demo.svg)

## 🚀 Quick Start

```bash
# No installation required — run directly:
python -m mindmap.presentation.cli --help

# Or install globally (optional):
pip install -e .
mm --help
```

**Create your first mind map in 30 seconds:**

```bash
# Create
mm new "Project Plan" --root "Q2 Goals" -o plan.mm.json

# View the tree
mm open plan.mm.json

# Add nodes
mm ls --doc plan.mm.json                          # get root id
mm add <root_id> "Feature A" --doc plan.mm.json
mm add <root_id> "Feature B" --doc plan.mm.json
mm add <feature_a_id> "Login" --doc plan.mm.json

# Style it
mm style <root_id> --fill "#2c3e50" --font-size 18 --doc plan.mm.json
mm style <feature_a_id> --fill "#3498db" --doc plan.mm.json

# Render to SVG
mm render plan.mm.json -o plan.svg

# Export to Markdown
mm to-md plan.mm.json -o plan.md
```

## 📖 Usage

### Commands Overview

| Command | Description |
|---------|-------------|
| `new` | Create a new mind map document |
| `open` | Print a tree view of the document |
| `ls` | List all nodes with their IDs |
| `add` | Add a child node under a parent |
| `edit` | Update a node's text or note |
| `rm` | Remove a subtree |
| `move` | Move a subtree under a new parent |
| `style` | Apply visual overrides to a node |
| `unstyle` | Remove visual overrides from a node |
| `to-md` | Export to Markdown |
| `from-md` | Import from Markdown |
| `render` | Render to SVG |

### Editing Workflow

```bash
# List nodes to get their IDs
mm ls --doc map.mm.json

# Add a child
mm add <parent_id> "New Node" --note "optional note" --index 0 --doc map.mm.json

# Edit a node
mm edit <node_id> --text "Updated Text" --note "new note" --doc map.mm.json

# Move a subtree
mm move <node_id> --to <new_parent_id> --index 0 --doc map.mm.json

# Remove a subtree
mm rm <node_id> --doc map.mm.json
```

### Styling Nodes

```bash
# Available style properties
mm style <node_id> \
  --fill "#e74c3c" \
  --stroke "#c0392b" \
  --text-color "#ffffff" \
  --font-size 16 \
  --font-weight "bold" \
  --border-radius 8 \
  --doc map.mm.json

# Clear style for a node
mm unstyle <node_id> --doc map.mm.json
```

### Markdown Interop

```bash
# Export to Markdown (lossy — IDs and styles not preserved)
mm to-md map.mm.json -o map.md

# Import from Markdown (regenerates IDs)
mm from-md map.md -o map.mm.json
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│  presentation/   CLI (argparse)                     │  ← swappable: Web / GUI
├─────────────────────────────────────────────────────┤
│  application/    Use-case orchestration             │
├─────────────────────────────────────────────────────┤
│  rendering/      SVG output + Theme  │  layout/     │  ← visualization
│                                   Balanced tree     │
├─────────────────────────────────────────────────────┤
│  convert/        Markdown bidir     │  storage/     │  ← exchange & persistence
│                                     │  Repository   │
├─────────────────────────────────────────────────────┤
│  domain/         Node · MindMap · StyleMap          │  ← zero dependencies
└─────────────────────────────────────────────────────┘
```

**Dependency rule:** Outer layers depend on inner layers. Inner layers never import from outer layers. The domain layer has zero imports outside the Python standard library — you could publish it as a standalone package.

## 📦 File Format

Mind maps are saved as `.mm.json` — a straightforward JSON document:

```json
{
  "id": "a1b2c3d4",
  "title": "My Map",
  "root": {
    "id": "e5f6g7h8",
    "text": "中心主题",
    "children": [
      { "id": "i9j0k1l2", "text": "Branch", "children": [] }
    ]
  },
  "styles": {
    "e5f6g7h8": { "fill": "#2c3e50", "text_color": "#ffffff" }
  }
}
```

- `styles` key is optional — old files without it load fine.
- All text is UTF-8. CJK characters remain readable in the raw JSON.
- Atomic writes: never get a truncated file on crash.

## 🧪 Tests

```bash
python -m unittest discover tests/ -v
```

115+ tests covering domain model, editing, layout, rendering, styling, storage, CLI, and backward compatibility.

## 🗺 Roadmap

- [x] **M1** — Core model, JSON persistence, Markdown conversion, CLI
- [x] **M2** — Auto-balanced layout, SVG rendering
- [x] **M3** — Node editing (add / edit / remove / move / list)
- [x] **M4** — Per-node style layer (Theme + StyleMap)
- [ ] **M5** — Interactive UI (drag, zoom, collapse)
- [ ] **Web** — React/Vue-based editor
- [ ] **Desktop** — Tauri or Electron wrapper

## 🤝 Contributing

This project is built for clarity. Contributions are welcome if they:

- **Add no new dependencies** — stdlib only, always.
- **Keep the domain layer pure** — no outer-layer concepts leak inward.
- **Follow existing patterns** — dataclasses, in-place mutation, `to_dict`/`from_dict` serialization.

Open an issue first to discuss your idea.

## 📄 License

MIT — free for any use.
