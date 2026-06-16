/* ── 主入口：初始化、事件绑定、生命周期 ──────────── */

const APP = {
  mindmap: null,     // mindmap JSON
  boxes: null,       // layout coordinates
  filePath: null,    // current file path
  isDirty: false,
  savedData: null,   // JSON.stringify 快照，用于 dirty 检测

  /** 从 URL 参数 ?path= 启动 */
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
      this.mindmap = data;
      this.boxes = boxes;
      this.filePath = filePath;
      this.savedData = JSON.stringify(data);
      this.isDirty = false;

      document.getElementById('filepath').textContent = filePath;
      this._updateSaveBtn();
      this._updateDirty();

      RENDERER.render(data, boxes);
      INTERACT.fitView();

      // 选中根节点
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
      this._updateSaveBtn();
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
    // 前端转换：从 JSON tree 生成 Markdown（轻量实现，不依赖服务端）
    try {
      const md = this._toMarkdown(this.mindmap);
      this._download(md, (this.filePath || 'mindmap').replace(/\.mm\.json$/, '') + '.md', 'text/markdown');
    } catch (err) {
      this._setError(`导出 Markdown 失败: ${err.message}`);
    }
  },

  /* ── 内部 ────────────────────────────────────── */

  _bindUI() {
    document.getElementById('btn-save').addEventListener('click', () => this.save());
    document.getElementById('btn-export-svg').addEventListener('click', () => this.exportSvg());
    document.getElementById('btn-export-md').addEventListener('click', () => this.exportMd());

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

    // 选中节点 → 更新保存按钮状态（后续可扩展为风格面板）
    INTERACT.onSelect = () => {};
    INTERACT.onDeselect = () => {};
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

  /** 简易 Markdown 导出（保持与 Python 版一致） */
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
};

// ── 启动 ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => APP.init());
