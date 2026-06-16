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
rendering/  SVG 输出   │  layout/ 平衡树    ← 只读可视化
convert/  Markdown 双向 │  storage/ Repo    ← 交换 & 持久化
domain/  Node + MindMap                   ← 核心，零依赖
```

依赖规则：外层依赖内层，内层不依赖外层。

## 功能

- 树形思维导图数据模型
- `.mm.json` 原生格式持久化（Repository 分层，可换实现）
- `.mm.json` ↔ Markdown 双向转换
- 左右平衡树自动布局
- 只读 SVG 矢量输出
- CLI 命令行工具

## 安装（可选）

```bash
pip install -e .
# 或直接用模块方式运行，无需安装：
python -m mindmap.presentation.cli --help
```

## 使用

```bash
mm new "我的导图" --root "中心主题" -o map.mm.json
mm open map.mm.json
mm to-md map.mm.json -o out.md
mm from-md in.md -o map.mm.json
mm render map.mm.json -o diag.svg
```

## 状态

- [x] M1 核心：模型 / 存储 / Markdown 转换 / CLI
- [x] M2 只读可视化：自动布局 + SVG
- [ ] M3 编辑（增删改 / 拖拽 / 缩放）
- [ ] UI 层（Web / 桌面）

## License

MIT
