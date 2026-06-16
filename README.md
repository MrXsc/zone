# mindmap

> A minimal, elegant, lightweight mind-mapping tool.
> Pure Python standard library. Zero dependencies. No database.

## 设计理念

- **极简**：只做必要的事，每一层都小到可以一眼读完。
- **解耦**：分层架构，依赖单向向内。核心 `domain/` 零依赖；未来加 UI / Web / 数据库只新增外层模块，核心不动。
- **轻量**：纯标准库，无需 `pip install` 任何第三方包。

## 架构

```
presentation/  CLI (argparse)              ← 入口，可替换为 Web/GUI
application/   用例服务编排
rendering/  SVG 输出 + Theme 主题  │  layout/ 平衡树   ← 可视化
convert/  Markdown 双向 │  storage/ Repo              ← 交换 & 持久化
domain/  Node + MindMap + NodeStyle + StyleMap        ← 核心，零依赖
```

依赖规则：外层依赖内层，内层不依赖外层。

## 功能

- 树形思维导图数据模型
- `.mm.json` 原生格式持久化（Repository 分层，可换实现）
- `.mm.json` ↔ Markdown 双向转换
- 左右平衡树自动布局
- SVG 矢量输出（支持主题 + 逐节点风格覆盖）
- CLI 命令行工具（含节点编辑与风格管理）
- **节点编辑**：增 / 删 / 改 / 移
- **风格层**：每个节点可独立设置 fill / stroke / text_color / font_size / font_weight / border_radius

## 安装（可选）

```bash
pip install -e .
# 或直接用模块方式运行，无需安装：
python -m mindmap.presentation.cli --help
```

## 使用

```bash
# 创建 / 查看 / 转换 / 渲染
mm new "我的导图" --root "中心主题" -o map.mm.json
mm open map.mm.json
mm to-md map.mm.json -o out.md
mm from-md in.md -o map.mm.json
mm render map.mm.json -o diag.svg

# 节点编辑（M3）
mm ls --doc map.mm.json                   # 列出所有节点 id + 文本
mm add <parent_id> "子节点" --doc map.mm.json      # 添加子节点
mm edit <node_id> --text "新文本" --doc map.mm.json # 修改节点文本
mm rm <node_id> --doc map.mm.json                  # 删除子树
mm move <node_id> --to <parent_id> --doc map.mm.json # 移动节点

# 风格覆盖（M4）
mm style <node_id> --fill "#e74c3c" --doc map.mm.json
mm style <node_id> --font-size 16 --font-weight bold --doc map.mm.json
mm unstyle <node_id> --doc map.mm.json
```

## 状态

- [x] M1 核心：模型 / 存储 / Markdown 转换 / CLI
- [x] M2 只读可视化：自动布局 + SVG
- [x] M3 节点编辑（增 / 删 / 改 / 移 / 列表）
- [x] M4 节点风格层（Theme + 逐节点覆盖）
- [ ] M5 拖拽 / 缩放交互（UI 层）
- [ ] Web UI（React / Vue）
- [ ] 桌面应用（Tauri / Electron）

## License

MIT
