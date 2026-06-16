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
};
