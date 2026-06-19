/* ── 主入口：初始化、事件绑定、生命周期 ──────────── */

const APP = {
  mindmap: null,     // mindmap JSON
  boxes: null,       // layout coordinates
  filePath: null,    // current file path
  isDirty: false,
  savedData: null,   // JSON.stringify 快照，用于 dirty 检测
  _undoStack: [],
  _redoStack: [],
  _maxUndo: 50,

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
    // 清空 undo/redo
    this._undoStack = [];
    this._redoStack = [];
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

  /** 通用：保存快照 → 执行 API 编辑 → 更新状态 → 重渲染 */
  async _performEdit(apiCall) {
    if (!this.mindmap) return;
    this._pushUndo();
    const selectedId = INTERACT.selectedId;
    this._showLoading(true);
    this._setError(null);
    try {
      const { mindmap, boxes } = await apiCall;
      this._setMap(mindmap, boxes, this.filePath);
      RENDERER.render(mindmap, boxes);
      if (selectedId && this._findNode(mindmap.root, selectedId)) {
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
      const parent = this._findNodeById(pid);
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
      const parent = this._findParentById(nid);
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
    const parent = this._findParentById(nid);
    const parentId = parent ? parent.id : null;
    await this._performEdit(API.deleteNode(this.mindmap, nid));
    // _performEdit 回退到 root，这里切到父节点
    if (parentId && this._findNode(this.mindmap.root, parentId)) {
      INTERACT.select(parentId);
    } else {
      INTERACT.select(this.mindmap.root.id);
    }
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
      const target = this._findNodeById(toParentId);
      if (target && target.id === nodeId) return;
      if (target && this._findNode(target, nodeId)) return; // 不能拖到自己的子树
    await this._performEdit(API.moveNode(this.mindmap, nodeId, toParentId));
  },

  /** 切换折叠/展开 */
  async toggleCollapse(nodeId) {
    await this._performEdit(API.toggleCollapse(this.mindmap, nodeId));
  },

  /* ── Undo / Redo ──────────────────────────── */

  /** 保存当前快照到 undo 栈（每次编辑前调用） */
  _pushUndo() {
    if (!this.mindmap) return;
    this._undoStack.push({
      mindmap: JSON.parse(JSON.stringify(this.mindmap)),
      boxes: JSON.parse(JSON.stringify(this.boxes)),
    });
    if (this._undoStack.length > this._maxUndo) this._undoStack.shift();
    this._redoStack = [];
  },

  undo() {
    if (this._undoStack.length === 0) return;
    // 当前状态推进 redo
    this._redoStack.push({
      mindmap: JSON.parse(JSON.stringify(this.mindmap)),
      boxes: JSON.parse(JSON.stringify(this.boxes)),
    });
    const prev = this._undoStack.pop();
    this._applyUndoState(prev);
  },

  redo() {
    if (this._redoStack.length === 0) return;
    this._undoStack.push({
      mindmap: JSON.parse(JSON.stringify(this.mindmap)),
      boxes: JSON.parse(JSON.stringify(this.boxes)),
    });
    const next = this._redoStack.pop();
    this._applyUndoState(next);
  },

  /** 恢复 undo/redo 状态（不碰 savedData，dirty 标记不受影响） */
  _applyUndoState(state) {
    this.mindmap = state.mindmap;
    this.boxes = state.boxes;
    RENDERER.render(this.mindmap, this.boxes);
    const id = INTERACT.selectedId;
    if (id && this._findNode(this.mindmap.root, id)) {
      INTERACT.select(id);
    } else {
      INTERACT.select(this.mindmap.root.id);
    }
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
    const box = this.boxes && this.boxes[nodeId];
    if (!box) { this._startEditPrompt(nodeId); return; }
    const node = this._findNodeById(nodeId);
    if (!node) return;

    try {
      const wrapper = document.getElementById('canvas-wrapper');
      const rect = wrapper.getBoundingClientRect();
      const scale = INTERACT.scale || 1;
      const tx = INTERACT.tx || 80;
      const ty = INTERACT.ty || 60;

      const x = box.x * scale + tx + rect.left;
      const y = box.y * scale + ty + rect.top;
      const w = Math.max(box.width * scale, 40);
      const h = Math.max(box.height * scale, 24);

      const input = document.createElement('input');
      input.className = 'inline-edit';
      input.type = 'text';
      input.value = node.text || '';
      input.style.left = x + 'px';
      input.style.top = y + 'px';
      input.style.width = w + 'px';
      input.style.height = h + 'px';
      try {
        const fs = RENDERER._resolveStyle(nodeId, nodeId === this.mindmap.root.id).fontSize;
        input.style.fontSize = (fs * scale) + 'px';
      } catch (_) { input.style.fontSize = '14px'; }

      this._editNodeId = nodeId;
      this._editInput = input;

      input.addEventListener('blur', () => this._finishEdit());
      input.addEventListener('keydown', (e) => {
        e.stopPropagation();  // 防止触发全局快捷键
        if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
        else if (e.key === 'Escape') { this._cancelEdit(); }
        else if (e.key === 'Tab') { e.preventDefault(); }
      });

      document.body.appendChild(input);
      input.focus();
      input.select();
    } catch (e) {
      this._startEditPrompt(nodeId);
    }
  },

  /** 降级：用浏览器 prompt 编辑 */
  _startEditPrompt(nodeId) {
    const node = this._findNodeById(nodeId);
    if (!node) return;
    const text = prompt('编辑节点文字：', node.text || '');
    if (text !== null) {
      this.updateNodeText(nodeId, text.trim() || ' ');
    }
  },

  async _finishEdit() {
    const input = this._editInput;
    const nodeId = this._editNodeId;
    if (!input || !nodeId) return;
    const text = input.value.trim();
    this._editInput = null;
    this._editNodeId = null;
    if (input.parentNode) input.parentNode.removeChild(input);
    await this.updateNodeText(nodeId, text || ' ');
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

  /* ── 样式面板 ──────────────────────────────── */

  _styleNodeId: null,
  _stylePanelVisible: false,

  _toggleStylePanel() {
    this._stylePanelVisible = !this._stylePanelVisible;
    document.getElementById('style-panel').classList.toggle('hidden', !this._stylePanelVisible);
    document.body.classList.toggle('style-mode', this._stylePanelVisible);
    if (this._stylePanelVisible && this.mindmap) {
      this._populateStylePanel(INTERACT.selectedId || this.mindmap.root.id);
    }
  },

  _closeStylePanel() {
    this._stylePanelVisible = false;
    document.getElementById('style-panel').classList.add('hidden');
    document.body.classList.remove('style-mode');
  },

  _getBtnGroupValues(groupId) {
    const btns = document.querySelectorAll('#' + groupId + ' .style-btn.active');
    return Array.from(btns).map(function(b) { return b.dataset.value; });
  },

  _populateStylePanel(nodeId) {
    this._styleNodeId = nodeId;
    const node = this._findNodeById(nodeId);
    if (!node) return;

    // 读取当前样式（合并主题默认值）
    const isRoot = nodeId === this.mindmap.root.id;
    const over = (this.mindmap.styles || {})[nodeId];
    const t = RENDERER.theme;
    const fill = over?.fill || (isRoot ? t.rootFill : t.nodeFill);
    const stroke = over?.stroke || (isRoot ? 'none' : t.nodeStroke);
    const textColor = over?.text_color || (isRoot ? t.rootText : t.ink);
    const fontSize = over?.font_size || t.fontSize;
    const fontWeight = over?.font_weight || (isRoot ? '600' : t.fontWeight);
    const fontStyle = over?.font_style || 'normal';
    const textDeco = over?.text_decoration || 'none';
    const textAlign = over?.text_align || 'center';

    document.getElementById('style-fill').value = fill;
    document.getElementById('style-stroke').value = stroke === 'none' ? '#c3cad2' : stroke;
    document.getElementById('style-text-color').value = textColor;
    document.getElementById('style-font-size').value = fontSize;

    // 字体按钮（B/I/S/U 可多选）
    document.getElementById('style-font-buttons').querySelectorAll('.style-btn').forEach(function(b) {
      var field = b.dataset.field;
      var val = b.dataset.value;
      var active = false;
      if (field === 'font_weight') active = (fontWeight === val);
      else if (field === 'font_style') active = (fontStyle === val);
      else if (field === 'text_decoration') active = (textDeco.indexOf(val) >= 0);
      b.classList.toggle('active', active);
    });

    // 对齐按钮（单选）
    document.getElementById('style-align-buttons').querySelectorAll('.style-btn').forEach(function(b) {
      b.classList.toggle('active', b.dataset.value === textAlign);
    });
  },

  _readToggleStyle() {
    // 从 B/I/S/U 按钮读取 font_weight / font_style / text_decoration
    var fontWeight = null;
    var fontStyle = null;
    var decorations = [];
    document.querySelectorAll('#style-font-buttons .style-btn.active').forEach(function(b) {
      var field = b.dataset.field;
      var val = b.dataset.value;
      if (field === 'font_weight') fontWeight = val;
      else if (field === 'font_style') fontStyle = val;
      else if (field === 'text_decoration') decorations.push(val);
    });
    return {
      font_weight: fontWeight,
      font_style: fontStyle,
      text_decoration: decorations.length ? decorations.join(' ') : null,
    };
  },

  async _applyStyle() {
    if (!this._styleNodeId || !this.mindmap) return;
    var toggle = this._readToggleStyle();
    var align = document.querySelector('#style-align-buttons .style-btn.active');
    const style = {
      fill: document.getElementById('style-fill').value,
      stroke: document.getElementById('style-stroke').value,
      text_color: document.getElementById('style-text-color').value,
      font_size: parseFloat(document.getElementById('style-font-size').value),
      font_weight: toggle.font_weight,
      font_style: toggle.font_style,
      text_decoration: toggle.text_decoration,
      text_align: align ? align.dataset.value : null,
    };
    await this._performEdit(API.setStyle(this.mindmap, this._styleNodeId, style));
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
    if (this._stylePanelVisible && this.mindmap) {
      this._populateStylePanel(INTERACT.selectedId || this.mindmap.root.id);
    }
  },

  _bindUI() {
    document.getElementById('btn-save').addEventListener('click', () => this.save());
    document.getElementById('btn-export-svg').addEventListener('click', () => this.exportSvg());
    document.getElementById('btn-export-md').addEventListener('click', () => this.exportMd());

    // 编辑工具栏按钮
    document.getElementById('btn-add-child')?.addEventListener('click', () => this.addChild());
    document.getElementById('btn-delete')?.addEventListener('click', () => this.deleteNode());
    document.getElementById('btn-undo')?.addEventListener('click', () => this.undo());
    document.getElementById('btn-redo')?.addEventListener('click', () => this.redo());
    document.getElementById('btn-style-toggle')?.addEventListener('click', () => this._toggleStylePanel());
    document.getElementById('btn-close-style')?.addEventListener('click', () => {
      this._closeStylePanel();
    });

    // 样式面板控件变更
    ['style-fill', 'style-stroke', 'style-text-color'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => this._applyStyle());
    });
    document.getElementById('style-font-size')?.addEventListener('change', () => this._applyStyle());
    // 字号输入框按回车立即应用（阻止冒泡避免触发导图快捷键）
    document.getElementById('style-font-size')?.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { e.stopPropagation(); e.target.blur(); }
    });
    // 字体/对齐按钮点击
    document.querySelectorAll('.style-btn').forEach(btn => {
      btn.addEventListener('click', function(e) {
        var group = this.closest('.style-btn-group');
        // 对齐按钮（单选）
        if (group && group.id === 'style-align-buttons') {
          group.querySelectorAll('.style-btn').forEach(function(b) { b.classList.remove('active'); });
          this.classList.add('active');
        } else {
          // 字体按钮（多选）
          this.classList.toggle('active');
        }
        APP._applyStyle();
      });
    });
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

    // 点击画布空白区域 → 关闭样式面板
    document.getElementById('canvas-wrapper')?.addEventListener('click', (e) => {
      if (this._stylePanelVisible && !e.target.closest('.node-group')) {
        this._closeStylePanel();
      }
    });

    // INTERACT 回调
    INTERACT.onSelect = (nodeId) => {
      this._cancelEdit();
      if (this._stylePanelVisible) this._closeStylePanel();
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
    INTERACT.onCollapseToggle = (nodeId) => {
      this.toggleCollapse(nodeId);
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

  /** 从 mindmap JSON 中查找节点（自动进入 root） */
  _findNodeById(id) {
    return this.mindmap ? this._findNode(this.mindmap.root, id) : null;
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

  /** 从 mindmap JSON 中查找父节点 */
  _findParentById(id) {
    return this.mindmap ? this._findParent(this.mindmap.root, id) : null;
  },
};

// ── 启动 ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => APP.init());
