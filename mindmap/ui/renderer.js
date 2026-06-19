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
    fontStyle: 'normal',
    textDecoration: 'none',
    textAlign: 'center',
    strokeWidth: 1.2,
    connector: '#9aa5b1',
  },

  /**
   * 渲染整张导图
   * @param {object} mindmap  - mindmap JSON（含 styles / collapsed）
   * @param {object} boxes    - node_id → {x, y, width, height}
   */
  render(mindmap, boxes) {
    this._mindmap = mindmap;
    this._boxes = boxes;
    this._styles = mindmap.styles || {};
    this._collapsed = new Set(mindmap.collapsed || []);

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
    const walk = this._walk(this._mindmap.root, this._collapsed);
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
    // 锚点 & x 坐标
    let anchor = 'middle';
    let tx = box.x + box.width / 2;
    if (style.textAlign === 'left') { anchor = 'start'; tx = box.x + style.fontSize * 0.5; }
    else if (style.textAlign === 'right') { anchor = 'end'; tx = box.x + box.width - style.fontSize * 0.5; }
    $text.setAttribute('x', tx);
    $text.setAttribute('y', box.y + box.height / 2 + style.fontSize * 0.35);
    $text.setAttribute('text-anchor', anchor);
    $text.setAttribute('fill', style.textColor);
    $text.setAttribute('font-family', this.theme.fontFamily);
    $text.setAttribute('font-size', style.fontSize);
    $text.setAttribute('font-weight', style.fontWeight);
    $text.setAttribute('font-style', style.fontStyle);
    $text.setAttribute('text-decoration', style.textDecoration);
    $text.textContent = node.text || ' ';
    $g.appendChild($text);

    // 折叠开关：仅对非叶子节点显示
    if (!isRoot && node.children && node.children.length > 0) {
      const isCollapsed = this._collapsed.has(node.id);
      const cx = box.x + box.width + 6;  // 右移避开文字
      const cy = box.y + box.height / 2;
      const r = 6;

      const $btn = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      $btn.setAttribute('class', 'collapse-toggle');
      $btn.dataset.nodeId = node.id;

      // 背景圆
      const $circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      $circle.setAttribute('cx', cx);
      $circle.setAttribute('cy', cy);
      $circle.setAttribute('r', r);
      $circle.setAttribute('fill', '#e2e8f0');
      $circle.setAttribute('stroke', '#94a3b8');
      $circle.setAttribute('stroke-width', '1');
      $btn.appendChild($circle);

      // +/- 图标（用路径画十字线）
      const $icon = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const s = 3; // half-length of the cross arms
      if (isCollapsed) {
        // 展开状态（已折叠）：画 + 
        $icon.setAttribute('d', `M ${cx - s} ${cy} L ${cx + s} ${cy} M ${cx} ${cy - s} L ${cx} ${cy + s}`);
      } else {
        // 折叠状态（未折叠）：画 -
        $icon.setAttribute('d', `M ${cx - s} ${cy} L ${cx + s} ${cy}`);
      }
      $icon.setAttribute('stroke', '#475569');
      $icon.setAttribute('stroke-width', '1.8');
      $icon.setAttribute('stroke-linecap', 'round');
      $btn.appendChild($icon);

      $g.appendChild($btn);
    }

    return $g;
  },

  /* ── 连线 ────────────────────────────────────── */

  _renderConnectors($container) {
    const walk = this._walk(this._mindmap.root, this._collapsed);
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
        fontStyle: over?.font_style || 'normal',
        textDecoration: over?.text_decoration || 'none',
        textAlign: over?.text_align || 'center',
        borderRadius: over?.border_radius || t.rootRx,
      };
    }
    return {
      fill: over?.fill || t.nodeFill,
      stroke: over?.stroke || t.nodeStroke,
      textColor: over?.text_color || t.ink,
      fontSize: over?.font_size || t.fontSize,
      fontWeight: over?.font_weight || t.fontWeight,
      fontStyle: over?.font_style || t.fontStyle,
      textDecoration: over?.text_decoration || t.textDecoration,
      textAlign: over?.text_align || t.textAlign,
      borderRadius: over?.border_radius || t.nodeRx,
    };
  },

  /* ── 树遍历 ──────────────────────────────────── */

  /** 深度优先遍历，跳过折叠节点的子树 */
  _walk(root, collapsed) {
    const result = [];
    function dfs(node) {
      result.push(node);
      if (node.children && !(collapsed && collapsed.has(node.id))) {
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
