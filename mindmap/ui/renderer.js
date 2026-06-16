/* ── SVG 渲染器：JSON + 布局坐标 → SVG DOM ────────── */

const RENDERER = {
  /** 主题默认值（对应 Python Theme 的 DEFAULT_THEME） */
  theme: {
    rootFill: '#1f2933',
    rootText: '#ffffff',
    rootRx: 8,
    nodeFill: '#ffffff',
    nodeStroke: '#c3cad2',
    nodeRx: 6,
    ink: '#1f2933',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
    fontSize: 14,
    fontWeight: '400',
    strokeWidth: 1.2,
    connector: '#9aa5b1',
  },

  /**
   * 渲染整张导图
   * @param {object} mindmap  - mindmap JSON（含 styles）
   * @param {object} boxes    - node_id → {x, y, width, height}
   */
  render(mindmap, boxes) {
    this._mindmap = mindmap;
    this._boxes = boxes;
    this._styles = mindmap.styles || {};

    const $connectors = document.getElementById('connectors');
    const $nodes = document.getElementById('nodes');
    $connectors.innerHTML = '';
    $nodes.innerHTML = '';

    // 1) 连线（先画，节点盖在上面）
    this._renderConnectors($connectors);

    // 2) 节点
    this._renderNodes($nodes);
  },

  /* ── 节点 ────────────────────────────────────── */

  _renderNodes($container) {
    const walk = this._walk(this._mindmap.root);
    for (const node of walk) {
      const box = this._boxes[node.id];
      if (!box) continue;
      const isRoot = node === this._mindmap.root;
      const style = this._resolveStyle(node.id, isRoot);

      const $g = this._createNodeGroup(node, box, style, isRoot);
      $container.appendChild($g);
    }
  },

  _createNodeGroup(node, box, style, isRoot) {
    const $g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    $g.setAttribute('class', 'node-group');
    $g.dataset.nodeId = node.id;

    // 圆角矩形
    const $rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    $rect.setAttribute('class', 'node-rect');
    $rect.setAttribute('x', box.x);
    $rect.setAttribute('y', box.y);
    $rect.setAttribute('width', box.width);
    $rect.setAttribute('height', box.height);
    $rect.setAttribute('rx', style.borderRadius);
    $rect.setAttribute('fill', style.fill);
    $rect.setAttribute('stroke', isRoot ? 'none' : style.stroke);
    $rect.setAttribute('stroke-width', this.theme.strokeWidth);
    $g.appendChild($rect);

    // 文字
    const $text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    $text.setAttribute('class', 'node-text');
    $text.setAttribute('x', box.x + box.width / 2);
    $text.setAttribute('y', box.y + box.height / 2 + style.fontSize * 0.35);
    $text.setAttribute('text-anchor', 'middle');
    $text.setAttribute('fill', style.textColor);
    $text.setAttribute('font-family', this.theme.fontFamily);
    $text.setAttribute('font-size', style.fontSize);
    $text.setAttribute('font-weight', style.fontWeight);
    $text.textContent = node.text || ' ';
    $g.appendChild($text);

    return $g;
  },

  /* ── 连线 ────────────────────────────────────── */

  _renderConnectors($container) {
    const walk = this._walk(this._mindmap.root);
    for (const parent of walk) {
      if (!parent.children || parent.children.length === 0) continue;
      const pbox = this._boxes[parent.id];
      if (!pbox) continue;

      for (const child of parent.children) {
        const cbox = this._boxes[child.id];
        if (!cbox) continue;

        const $path = this._createConnector(pbox, cbox);
        $container.appendChild($path);
      }
    }
  },

  _createConnector(pbox, cbox) {
    const pcx = pbox.x + pbox.width / 2;
    const pcy = pbox.y + pbox.height / 2;
    const ccx = cbox.x + cbox.width / 2;
    const ccy = cbox.y + cbox.height / 2;

    let x0, y0, x1, y1;
    if (ccx >= pcx) {
      x0 = pbox.x + pbox.width; y0 = pcy;
      x1 = cbox.x; y1 = ccy;
    } else {
      x0 = pbox.x; y0 = pcy;
      x1 = cbox.x + cbox.width; y1 = ccy;
    }
    const dx = (x1 - x0) * 0.5;
    const cx0 = x0 + dx, cy0 = y0;
    const cx1 = x1 - dx, cy1 = y1;

    const $path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    $path.setAttribute('d', `M ${x0} ${y0} C ${cx0} ${cy0}, ${cx1} ${cy1}, ${x1} ${y1}`);
    $path.setAttribute('fill', 'none');
    $path.setAttribute('stroke', this.theme.connector);
    $path.setAttribute('stroke-width', this.theme.strokeWidth);
    return $path;
  },

  /* ── 风格解析 ────────────────────────────────── */

  _resolveStyle(nodeId, isRoot) {
    const over = this._styles[nodeId];
    const t = this.theme;

    if (isRoot) {
      return {
        fill: over?.fill || t.rootFill,
        stroke: 'none',
        textColor: over?.text_color || t.rootText,
        fontSize: over?.font_size || t.fontSize,
        fontWeight: over?.font_weight || '600',
        borderRadius: over?.border_radius || t.rootRx,
      };
    }
    return {
      fill: over?.fill || t.nodeFill,
      stroke: over?.stroke || t.nodeStroke,
      textColor: over?.text_color || t.ink,
      fontSize: over?.font_size || t.fontSize,
      fontWeight: over?.font_weight || t.fontWeight,
      borderRadius: over?.border_radius || t.nodeRx,
    };
  },

  /* ── 树遍历 ──────────────────────────────────── */

  _walk(root) {
    const result = [];
    function dfs(node) {
      result.push(node);
      if (node.children) {
        for (const c of node.children) dfs(c);
      }
    }
    dfs(root);
    return result;
  },

  /** 获取选中节点的 SVG 边界框 */
  getNodeBox(nodeId) {
    return this._boxes[nodeId] || null;
  },
};
