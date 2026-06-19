/* ── API 通信层 ────────────────────────────────────── */

const API = {
  /** 从服务端加载 .mm.json，返回 mindmap JSON */
  async loadMap(filePath) {
    const res = await fetch(`/api/map?path=${encodeURIComponent(filePath)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /** 保存 mindmap JSON 到服务端 */
  async saveMap(filePath, data) {
    const res = await fetch(`/api/map?path=${encodeURIComponent(filePath)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /** 请求布局坐标：传入 mindmap JSON，返回 node_id → {x,y,w,h} */
  async layout(data) {
    const res = await fetch('/api/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /** 请求 SVG 渲染：传入 mindmap JSON，返回 SVG 字符串 */
  async render(data) {
    const res = await fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const json = await res.json();
    return json.svg;
  },

  /* ── 编辑 API ─────────────────────────────── */

  /** 通用编辑：POST 到指定端点，返回 {mindmap, boxes} */
  async _edit(endpoint, body) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /** 添加子节点 */
  async addChild(mindmap, parentId, text, index) {
    return this._edit('/api/node/add-child', { mindmap, parent_id: parentId, text, index });
  },

  /** 添加兄弟节点 (before=true 在上方) */
  async addSibling(mindmap, nodeId, text, before) {
    return this._edit('/api/node/add-sibling', { mindmap, node_id: nodeId, text, before });
  },

  /** 添加父节点 */
  async addParent(mindmap, nodeId, text) {
    return this._edit('/api/node/add-parent', { mindmap, node_id: nodeId, text });
  },

  /** 更新节点文字/备注 */
  async updateNode(mindmap, nodeId, text, note) {
    return this._edit('/api/node/update', { mindmap, node_id: nodeId, text, note });
  },

  /** 删除节点 */
  async deleteNode(mindmap, nodeId) {
    return this._edit('/api/node/delete', { mindmap, node_id: nodeId });
  },

  /** 移动节点到新父节点 */
  async moveNode(mindmap, nodeId, toParentId, index) {
    return this._edit('/api/node/move', { mindmap, node_id: nodeId, to_parent_id: toParentId, index });
  },

  /** 上移/下移兄弟节点 */
  async reorderNode(mindmap, nodeId, direction) {
    return this._edit('/api/node/reorder', { mindmap, node_id: nodeId, direction });
  },

  /** 切换折叠/展开 */
  async toggleCollapse(mindmap, nodeId) {
    return this._edit('/api/node/toggle-collapse', { mindmap, node_id: nodeId });
  },

  /** 设置节点样式 */
  async setStyle(mindmap, nodeId, style) {
    return this._edit('/api/node/style', { mindmap, node_id: nodeId, style });
  },
};
