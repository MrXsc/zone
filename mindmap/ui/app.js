/* ── 主入口：初始化、事件绑定、生命周期 ──────────── */

const APP = {
  mindmap: null,     // mindmap JSON
  boxes: null,       // layout coordinates
  filePath: null,    // current file path
  isDirty: false,
  savedData: null,   // JSON.stringify 快照，用于 dirty 检测

  /* ── 初始化 ────────────────────────────────── */

  async init() {
    INTERACT.init();
    this._bindUI();

    const params = new URLSearchParams(window.location.search);
    const path = params.get('path');
    if (path) {
      await this.load(path);
    } else {
      this._setStatus('?path= 参数未指定');
    }
  },

  /** 加载导图 */
  async load(filePath) {
    this._showLoading(true);
    this._setError(null);
    try {
      const data = await API.loadMap(filePath);
      const boxes = await API.layout(data);
      this._setMap(data, boxes, filePath);
      RENDERER.render(data, boxes);
      INTERACT.fitView();
      INTERACT.select(data.root.id);
    } catch (err) {
      this._setError(err.message);
    } finally {
      this._showLoading(false);
    }
  },

  /** 保存 */
  async save() {
    if (!this.filePath || !this.mindmap) return;
    this._showLoading(true);
    this._setError(null);
    try {
      await API.saveMap(this.filePath, this.mindmap);
      this.savedData = JSON.stringify(this.mindmap);
      this.isDirty = false;
      this._updateDirty();
    } catch (err) {
      this._setError(`保存失败: ${err.message}`);
    } finally {
      this._showLoading(false);
    }
  },

  /** 导出 SVG */
  async exportSvg() {
    if (!this.mindmap) return;
    try {
      const svg = await API.render(this.mindmap);
      this._download(svg, (this.filePath || 'mindmap').replace(/\.mm\.json$/, '') + '.svg', 'image/svg+xml');
    } catch (err) {
      this._setError(`导出 SVG 失败: ${err.message}`);
    }
  },

  /** 导出 Markdown */
  async exportMd() {
    if (!this.mindmap) return;
    try {
      const md = this._toMarkdown(this.mindmap);
      this._download(md, (this.filePath || 'mindmap').replace(/\.mm\.json$/, '') + '.md', 'text/markdown');
    } catch (err) {
      this._setError(`导出 Markdown 失败: ${err.message}`);
    }
  },

  /* ── 编辑操作 ──────────────────────────────── */

  /** 通用：执行 API 编辑 → 更新状态 → 重渲染 */
  async _performEdit(apiCall) {
    if (!this.mindmap) return;
    const selectedId = INTERACT.selectedId;
    this._showLoading(true);
    this._setError(null);
    try {
      const { mindmap, boxes } = await apiCall;
      this._setMap(mindmap, boxes, this.filePath);
      RENDERER.render(mindmap, boxes);
      INTERACT.fitView();
      if (selectedId && this._findNode(mindmap, selectedId)) {
        INTERACT.select(selectedId);
      } else {
        INTERACT.select(mindmap.root.id);
      }
    } catch (err) {
      this._setError(err.message);
    } finally {
      this._showLoading(false);
    }
  },

  /** 添加子节点 */
  async addChild() {
    const pid = INTERACT.selectedId || this.mindmap.root.id;
    await this._performEdit(API.addChild(this.mindmap, pid, '新节点'));
    // 选中新节点（最后一个子节点）
    const parent = this._findNode(this.mindmap, pid);
    if (parent && parent.children && parent.children.length > 0) {
      const last = parent.children[parent.children.length - 1];
      INTERACT.select(last.id);
    }
    this._startEdit(INTERACT.selectedId);
  },

  /** 添加兄弟节点 */
  async addSibling(before) {
    const nid = INTERACT.selectedId;
    if (!nid || nid === this.mindmap.root.id) {
      await this.addChild(); // root → add child instead
      return;
    }
    await this._performEdit(API.addSibling(this.mindmap, nid, '新节点', before));
    // 选中新增的兄弟
    const parent = this._findParent(this.mindmap, nid);
    if (parent && parent.children) {
      const origIdx = parent.children.findIndex(c => c.id === nid);
      const newIdx = before ? origIdx : origIdx + 1;
      if (newIdx >= 0 && newIdx < parent.children.length) {
        INTERACT.select(parent.children[newIdx].id);
      }
    }
    this._startEdit(INTERACT.selectedId);
  },

  /** 添加父节点 */
  async addParent() {
    const nid = INTERACT.selectedId;
    if (!nid || nid === this.mindmap.root.id) return;
    await this._performEdit(API.addParent(this.mindmap, nid, '新父节点'));
    // 选中新父节点（根的第一个子节点）
    if (this.mindmap.root.children && this.mindmap.root.children.length > 0) {
      INTERACT.select(this.mindmap.root.children[0].id);
    }
    this._startEdit(INTERACT.selectedId);
  },

  /** 删除节点 */
  async deleteNode() {
    const nid = INTERACT.selectedId;
    if (!nid || nid === this.mindmap.root.id) return;
    await this._performEdit(API.deleteNode(this.mindmap, nid));
  },

  /** 上移 / 下移 */
  async reorderNode(direction) {
    const nid = INTERACT.selectedId;
    if (!nid || nid === this.mindmap.root.id) return;
    await this._performEdit(API.reorderNode(this.mindmap, nid, direction));
  },

  /** 移动节点到新父节点（拖拽） */
  async moveNode(nodeId, toParentId) {
    if (nodeId === toParentId || nodeId === this.mindmap.root.id) return;
    // 检查是否拖到自己子节点中
    const target = this._findNode(this.mindmap, toParentId);
    if (target && target.id === nodeId) return;
    if (target && this._findNode(target, nodeId)) return; // 不能拖到自己的子树
    await this._performEdit(API.moveNode(this.mindmap, nodeId, toParentId));
  },

  /** 更新节点文字 */
  async updateNodeText(nodeId, text) {
    await this._performEdit(API.updateNode(this.mindmap, nodeId, text));
  },

  /* ── 内联编辑 ──────────────────────────────── */

  _editNodeId: null,
  _editInput: null,

  _startEdit(nodeId) {
    if (!nodeId) return;
    this._cancelEdit();
    const box = this.boxes[nodeId];
    if (!box) return;

    const node = this._findNode(this.mindmap, nodeId);
    if (!node) return;

    const wrapper = document.getElementById('canvas-wrapper');
    const rect = wrapper.getBoundingClientRect();

    // 考虑缩放和平移
    const x = box.x * INTERACT.scale + INTERACT.tx + rect.left;
    const y = box.y * INTERACT.scale + INTERACT.ty + rect.top;
    const w = box.width * INTERACT.scale;
    const h = box.height * INTERACT.scale;

    const input = document.createElement('input');
    input.className = 'inline-edit';
    input.type = 'text';
    input.value = node.text || '';
    input.style.left = x + 'px';
    input.style.top = y + 'px';
    input.style.width = Math.max(w, 40) + 'px';
    input.style.height = h + 'px';
    input.style.fontSize = (RENDERER._resolveStyle(nodeId, nodeId === this.mindmap.root.id).fontSize * INTERACT.scale) + 'px';

    this._editNodeId = nodeId;
    this._editInput = input;

    input.addEventListener('blur', () => this._finishEdit());
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        input.blur();
      } else if (e.key === 'Escape') {
        this._cancelEdit();
      }
    });

    wrapper.appendChild(input);
    input.focus();
    input.select();
  },

  async _finishEdit() {
    const input = this._editInput;
    const nodeId = this._editNodeId;
    if (!input || !nodeId) return;
    const text = input.value.trim();
    this._editInput = null;
    this._editNodeId = null;
    if (input.parentNode) input.parentNode.removeChild(input);
    if (text) {
      await this.updateNodeText(nodeId, text);
    }
  },

  _cancelEdit() {
    if (this._editInput) {
      if (this._editInput.parentNode) {
        this._editInput.parentNode.removeChild(this._editInput);
      }
      this._editInput = null;
      this._editNodeId = null;
    }
  },

  /* ── 上下文菜单 ────────────────────────────── */

  _showContextMenu(x, y, nodeId) {
    this._hideContextMenu();
    const menu = document.getElementById('context-menu');
    if (!menu) return;
    menu.dataset.nodeId = nodeId;
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.classList.remove('hidden');
  },

  _hideContextMenu() {
    const menu = document.getElementById('context-menu');
    if (menu) menu.classList.add('hidden');
  },

  /* ── 内部 ────────────────────────────────────── */

  _setMap(mindmap, boxes, filePath) {
    this.mindmap = mindmap;
    this.boxes = boxes;
    if (filePath) this.filePath = filePath;
    this.savedData = JSON.stringify(mindmap);
    this.isDirty = false;
    if (filePath) {
      document.getElementById('filepath').textContent = filePath;
    }
    this._updateDirty();
    this._updateSaveBtn();
  },

  _bindUI() {
    document.getElementById('btn-save').addEventListener('click', () => this.save());
    document.getElementById('btn-export-svg').addEventListener('click', () => this.exportSvg());
    document.getElementById('btn-export-md').addEventListener('click', () => this.exportMd());

    // 编辑工具栏按钮
    document.getElementById('btn-add-child')?.addEventListener('click', () => this.addChild());
    document.getElementById('btn-delete')?.addEventListener('click', () => this.deleteNode());

    // 上下文菜单项
    document.getElementById('ctx-add-child')?.addEventListener('click', () => {
      const id = document.getElementById('context-menu')?.dataset.nodeId;
      if (id) { INTERACT.select(id); this.addChild(); }
      this._hideContextMenu();
    });
    document.getElementById('ctx-add-sibling')?.addEventListener('click', () => {
      const id = document.getElementById('context-menu')?.dataset.nodeId;
      if (id) { INTERACT.select(id); this.addSibling(false); }
      this._hideContextMenu();
    });
    document.getElementById('ctx-add-parent')?.addEventListener('click', () => {
      const id = document.getElementById('context-menu')?.dataset.nodeId;
      if (id) { INTERACT.select(id); this.addParent(); }
      this._hideContextMenu();
    });
    document.getElementById('ctx-edit')?.addEventListener('click', () => {
      const id = document.getElementById('context-menu')?.dataset.nodeId;
      if (id) this._startEdit(id);
      this._hideContextMenu();
    });
    document.getElementById('ctx-delete')?.addEventListener('click', () => {
      const id = document.getElementById('context-menu')?.dataset.nodeId;
      if (id) { INTERACT.select(id); this.deleteNode(); }
      this._hideContextMenu();
    });

    // 点击空白处隐藏菜单
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#context-menu')) this._hideContextMenu();
    });

    // Ctrl+S 保存
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        this.save();
      }
    });

    // 关页面前提示未保存
    window.addEventListener('beforeunload', (e) => {
      if (this.isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    });

    // INTERACT 回调
    INTERACT.onSelect = (nodeId) => {
      this._cancelEdit();
    };
    INTERACT.onDeselect = () => {
      this._cancelEdit();
    };
    INTERACT.onDoubleClick = (nodeId) => {
      this._startEdit(nodeId);
    };
    INTERACT.onContextMenu = (x, y, nodeId) => {
      this._showContextMenu(x, y, nodeId);
    };
    INTERACT.onNodeDrop = (nodeId, targetId) => {
      this.moveNode(nodeId, targetId);
    };
  },

  _updateDirty() {
    const $ind = document.getElementById('dirty-indicator');
    if (this.isDirty) {
      $ind.textContent = '●';
      $ind.classList.remove('hidden');
    } else {
      $ind.classList.add('hidden');
    }
  },

  _updateSaveBtn() {
    document.getElementById('btn-save').disabled = !this.mindmap;
  },

  _setError(msg) {
    const $el = document.getElementById('error-msg');
    if (msg) {
      $el.textContent = msg;
      $el.classList.remove('hidden');
      setTimeout(() => $el.classList.add('hidden'), 5000);
    } else {
      $el.classList.add('hidden');
    }
  },

  _showLoading(v) {
    document.getElementById('loading').classList.toggle('hidden', !v);
  },

  _setStatus(msg) {
    document.getElementById('filepath').textContent = msg;
  },

  _download(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  /** 简易 Markdown 导出 */
  _toMarkdown(data) {
    const lines = [];
    if (data.title) {
      lines.push(`# ${data.title}`, '');
    }
    const _emit = (node, depth) => {
      lines.push('  '.repeat(depth) + `- ${node.text || ''}`);
      if (node.children) {
        for (const c of node.children) _emit(c, depth + 1);
      }
    };
    _emit(data.root, 0);
    return lines.join('\n') + '\n';
  },

  /* ── 树查询 ────────────────────────────────── */

  _findNode(root, id) {
    if (!root) return null;
    if (root.id === id) return root;
    if (root.children) {
      for (const c of root.children) {
        const found = this._findNode(c, id);
        if (found) return found;
      }
    }
    return null;
  },

  _findParent(root, id) {
    if (!root || !root.children) return null;
    for (const c of root.children) {
      if (c.id === id) return root;
      const found = this._findParent(c, id);
      if (found) return found;
    }
    return null;
  },
};

// ── 启动 ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => APP.init());
