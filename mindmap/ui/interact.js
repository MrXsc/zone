/* ── 交互控制：缩放 / 平移 / 选中 ─────────────────── */

const INTERACT = {
  /* ---- 状态 ---- */
  scale: 1,
  tx: 0,
  ty: 0,
  isPanning: false,
  panStartX: 0,
  panStartY: 0,
  panStartTx: 0,
  panStartTy: 0,
  selectedId: null,

  /** 初始化（绑定事件） */
  init() {
    const wrapper = document.getElementById('canvas-wrapper');
    const viewport = document.getElementById('viewport');

    // ---- 缩放 ----
    wrapper.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = wrapper.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const delta = -e.deltaY * 0.001;
      const factor = 1 + Math.min(Math.max(delta, -0.3), 0.3);
      const newScale = Math.min(Math.max(this.scale * factor, 0.1), 5);

      // 以鼠标位置为中心缩放
      this.tx = mx - (mx - this.tx) * (newScale / this.scale);
      this.ty = my - (my - this.ty) * (newScale / this.scale);
      this.scale = newScale;
      this._applyTransform();
    }, { passive: false });

    // ---- 平移 ----
    wrapper.addEventListener('mousedown', (e) => {
      // 只在空白区域或画布背景上触发平移
      if (e.target === wrapper || e.target.id === 'canvas' ||
          e.target.id === 'viewport' || e.target.id === 'connectors' ||
          e.target.id === 'nodes') {
        this.isPanning = true;
        this.panStartX = e.clientX;
        this.panStartY = e.clientY;
        this.panStartTx = this.tx;
        this.panStartTy = this.ty;
      }
    });
    window.addEventListener('mousemove', (e) => {
      if (this.isPanning) {
        this.tx = this.panStartTx + (e.clientX - this.panStartX);
        this.ty = this.panStartTy + (e.clientY - this.panStartY);
        this._applyTransform();
      }
    });
    window.addEventListener('mouseup', () => {
      this.isPanning = false;
    });

    // ---- 选中节点 ----
    wrapper.addEventListener('click', (e) => {
      const $g = e.target.closest('.node-group');
      if ($g) {
        this.select($g.dataset.nodeId);
      } else if (e.target === wrapper || e.target.id === 'canvas' ||
                 e.target.id === 'viewport') {
        this.deselect();
      }
    });

    // ---- 键盘 ----
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.deselect();
      }
    });

    // ---- touch 支持（移动端手势） ----
    let touches = [];
    let lastDist = 0;
    wrapper.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isPanning = true;
        this.panStartX = e.touches[0].clientX;
        this.panStartY = e.touches[0].clientY;
        this.panStartTx = this.tx;
        this.panStartTy = this.ty;
      } else if (e.touches.length === 2) {
        this.isPanning = false;
        touches = [e.touches[0], e.touches[1]];
        lastDist = Math.hypot(
          touches[0].clientX - touches[1].clientX,
          touches[0].clientY - touches[1].clientY
        );
      }
    }, { passive: true });
    wrapper.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && this.isPanning) {
        this.tx = this.panStartTx + (e.touches[0].clientX - this.panStartX);
        this.ty = this.panStartTy + (e.touches[0].clientY - this.panStartY);
        this._applyTransform();
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / lastDist;
        const newScale = Math.min(Math.max(this.scale * factor, 0.1), 5);
        this.scale = newScale;
        lastDist = dist;
        this._applyTransform();
      }
    }, { passive: true });
    wrapper.addEventListener('touchend', () => {
      this.isPanning = false;
    }, { passive: true });
  },

  /** 选中节点 */
  select(nodeId) {
    this.deselect();
    this.selectedId = nodeId;
    const $g = document.querySelector(`.node-group[data-node-id="${nodeId}"]`);
    if ($g) $g.classList.add('selected');
    // 触发选中回调
    if (this.onSelect) this.onSelect(nodeId);
  },

  /** 取消选中 */
  deselect() {
    if (this.selectedId) {
      const $old = document.querySelector(`.node-group[data-node-id="${this.selectedId}"]`);
      if ($old) $old.classList.remove('selected');
      this.selectedId = null;
      if (this.onDeselect) this.onDeselect();
    }
  },

  /** 重置视图（适配全部节点） */
  fitView() {
    this.scale = 1;
    this.tx = 80;
    this.ty = 60;
    this._applyTransform();
  },

  /** 应用 SVG transform */
  _applyTransform() {
    const $vp = document.getElementById('viewport');
    $vp.setAttribute('transform', `translate(${this.tx}, ${this.ty}) scale(${this.scale})`);
  },
};
