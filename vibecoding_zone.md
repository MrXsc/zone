# vibecoding_zone — MindMap Tool

## 设计哲学

- **极简依赖** — 零 npm、零构建工具、零前端框架。纯 HTML + SVG + Vanilla JS
- **Flask 优先** — 后端用 Flask，不用 http.server 的杂乱路由
- **好看是硬需求** — "网页一定要设计的好看"，UI 审美不能妥协
- **XMind 肌肉记忆** — 快捷键与 XMind 完全一致：Tab(子节点) Enter(兄弟) Shift+Enter(父) Ctrl+Enter(同级) F2(编辑) Delete(删除) Alt+↑↓(移动)

## 架构原则

- **大块切分** — 架构图只分两大块：Frontend（Web UI）和 Data Plane（server + core engine + CLI），拒绝细碎分层
- **嵌套表达** — 框里套框表达层级关系，不用复杂连线流程图
- **避免特殊字符** — ASCII 图中不用 `·` 等非常规字符，避免编码/渲染问题
- **扁平化** — service 层合并到 CLI，减少架构层数（`application/services.py` → `presentation/cli.py`）
- **全量响应** — 每个编辑 API 返回 `{mindmap, boxes}`，前端拿到即渲染，不二次请求

## 工程约束

| 约束 | 原因 |
|------|------|
| 无 npm / node_modules | "直接用vue react 太重了" |
| Python stdlib + Flask only | Flask 是最重的额外依赖 |
| 无前端构建 | 删掉 build 环节，改完直接看 |
| 手动保存 + Ctrl+S | 无 autosave，dirty 检测靠 JSON.stringify 快照对比 |
| SVG 做 UI | JS 直接操作 DOM 元素，不用 canvas 重绘 |
| 布局服务端算 | 每次 mutation 后回算坐标，前端只渲染 boxes 数组 |
| URL 传文件 | `?path=examples/os_demo.mm.json` |

## 项目结构

```
zone/
├── server.py                  # Flask API 入口（11 个端点）
├── mindmap/
│   ├── domain/
│   │   ├── node.py            # 节点模型
│   │   ├── mindmap.py         # 增删改查 + 移动 + 重排
│   │   └── style.py           # NodeStyle / StyleMap / Theme
│   ├── layout/
│   │   └── balanced.py        # 平衡树布局算法
│   ├── rendering/
│   │   └── svg.py             # SVG 渲染 + 主题样式
│   ├── storage/
│   │   └── json_file.py       # .mm.json 序列化
│   ├── presentation/
│   │   └── cli.py             # CLI 命令行 + MindMapService
│   └── ui/                    # Web 前端
│       ├── index.html         # 页面 + 工具栏 + 右键菜单 DOM
│       ├── style.css          # 毛玻璃顶栏 / 上下文菜单 / 拖拽
│       ├── api.js             # fetch 封装
│       ├── app.js             # 状态管理 + 编辑方法
│       ├── interact.js        # 交互：缩放 / 拖拽 / 键盘 / 右键
│       └── renderer.js        # JSON → SVG 客户端渲染
└── tests/                     # 47 个测试
```

## 交互实现要点

- **内联编辑** — `position:fixed` input 浮层 + `stopPropagation()` 隔离键盘事件
- **拖拽移动** — mousedown/mousemove 检测阈值 5px + ghost 元素跟随
- **右键菜单** — contextmenu 事件 + 自定义 `position:fixed` 菜单
- **空文本保护** — 清空内容自动填入空格，保证节点不消失
- **拖拽与编辑互斥** — mousedown 检查 `e.button` 过滤右键，双击走独立 dblclick 事件

## API 端点

```
GET    /api/map              # 加载 .mm.json
POST   /api/layout           # 计算布局坐标
POST   /api/render           # 渲染 SVG 字符串
POST   /api/node/add-child   # 添加子节点
POST   /api/node/add-sibling # 添加兄弟节点
POST   /api/node/add-parent  # 添加父节点
POST   /api/node/update      # 更新文本/样式
POST   /api/node/delete      # 删除节点
POST   /api/node/move        # 移动节点
POST   /api/node/reorder     # 重排兄弟顺序
```

## 关键弯路 & 教训

| 问题 | 教训 |
|------|------|
| `_findNode` 查了 `this.mindmap` 而非 `this.mindmap.root` | 方法调用前确认对象图结构 |
| 编辑时 Tab/Enter 触发了全局快捷键 | 编辑 input 必须 `stopPropagation()` |
| 双击编辑同时触发了 mousedown 和 dblclick | 不要手动判双击，直接用 dblclick 事件 |
| 右键 mousedown 触发了拖拽检测 | 加 `e.button !== 0` 过滤 |
| `·` 在图里出编码问题 | ASCII 图只用常见字符 |
| 编辑 input 粘贴了多行文本 | 单行 input + 过滤换行符 |
| architecture 图太细碎 | 大块切分 + 框里套框，不画复杂连线 |

## 启动

```bash
pip install flask
python server.py --doc examples/os_demo.mm.json
# 浏览器打开 http://localhost:5000
```

## 路线图

- [x] Phase 1: CLI 模型 + Web UI 查看器
- [x] Phase 2: Web UI 编辑交互 + XMind 快捷键
- [ ] Phase 3a: 折叠/展开分支
- [ ] Phase 3b: Web UI 样式面板
- [ ] Phase 3c: Undo/Redo
