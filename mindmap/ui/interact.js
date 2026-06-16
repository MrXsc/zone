/* ── 交互控制：缩放 / 平移 / 选中 / 编辑 / 拖拽 ──── */

const INTERACT = {
  /* ---- 状态 ---- */
  scale: 1,
  tx: 80,
  ty: 60,
  selectedId: null,

  // 平移
  _isPanning: false,
  _panStartX: 0,
  _panStartY: 0,
  _panStartTx: 0,
  _panStartTy: 0,

  // 拖拽
  _isDragging: false,
  _dragNodeId: null,
  _dragStartX: 0,
  _dragStartY: 0,
  _dragGhost: null,
  _dropTargetId: null,

  // 点击判别
  _mouseDownX: 0,
  _mouseDownY: 0,
  _mouseDownNodeId: null,
  _mouseDownTime: 0,

  // 回调（由 APP 设置）
  onSelect: null,
  onDeselect: null,
  onDoubleClick: null,
  onContextMenu: null,
  onNodeDrop: null,

  /** 初始化 */
  init() {
    const wrapper = document.getElementById('canvas-wrapper');

    /* ══════ 鼠标事件 ══════ */

    // ---- 鼠标按下：区分空白（平移）与节点（拖拽） ----
    wrapper.addEventListener('mousedown', (e) => {
      this._mouseDownX = e.clientX;
      this._mouseDownY = e.clientY;
      this._mouseDownTime = Date.now();
      this._mouseDownButton = e.button;   // 0=left, 2=right
      const $g = e.target.closest('.node-group');
      this._mouseDownNodeId = $g ? $g.dataset.nodeId : null;

      if ($g && e.button === 0) {
        // 左键节点上按下 → 选中 + 准备拖拽
        this.select($g.dataset.nodeId);
        this._isDragging = false;
      } else if ($g && e.button === 2) {
        // 右键节点 → 选中 + 显示上下文菜单（通过 contextmenu 事件处理）
        this.select($g.dataset.nodeId);
      } else if (
        e.target === wrapper || e.target.id === 'canvas' ||
        e.target.id === 'viewport' || e.target.id === 'connectors' ||
        e.target.id === 'nodes'
      ) {
        // 空白区域 → 平移
        this._isPanning = true;
        this._panStartX = e.clientX;
        this._panStartY = e.clientY;
        this._panStartTx = this.tx;
        this._panStartTy = this.ty;
      }
    });

    // ---- 鼠标移动 ----
    window.addEventListener('mousemove', (e) => {
      // 平移
      if (this._isPanning) {
        this.tx = this._panStartTx + (e.clientX - this._panStartX);
        this.ty = this._panStartTy + (e.clientY - this._panStartY);
        this._applyTransform();
        return;
      }

      // 拖拽（节点上按下且移动超过阈值）
      if (this._mouseDownNodeId && !this._isPanning) {
        const dx = e.clientX - this._mouseDownX;
        const dy = e.clientY - this._mouseDownY;
        if (!this._isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
          this._isDragging = true;
          this._dragNodeId = this._mouseDownNodeId;
          this._startDrag(e);
        }
        if (this._isDragging) {
          this._moveDrag(e);
        }
      }
    });

    // ---- 鼠标释放 ----
    window.addEventListener('mouseup', (e) => {
      // 拖拽结束
      if (this._isDragging) {
        this._endDrag(e);
        this._isDragging = false;
        this._dragNodeId = null;
        this._mouseDownNodeId = null;
        return;
      }

      // 判定：点击 vs 拖拽（没移动就是点击）
      // 单击已在 mousedown 时 select，这里只清除状态
      if (this._mouseDownNodeId && !this._isPanning) {
        // no-op: select already happened in mousedown
      }

      this._isPanning = false;
      this._mouseDownNodeId = null;
    });

    // ---- 双击（独立监听，兜底） ----
    wrapper.addEventListener('dblclick', (e) => {
      const $g = e.target.closest('.node-group');
      if ($g && this.onDoubleClick) {
        this.onDoubleClick($g.dataset.nodeId);
      }
    });

    // ---- 右键菜单 ----
    wrapper.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const $g = e.target.closest('.node-group');
      if ($g && this.onContextMenu) {
        this.select($g.dataset.nodeId);
        this.onContextMenu(e.clientX, e.clientY, $g.dataset.nodeId);
      }
    });

    /* ══════ 键盘事件 ══════ */

    window.addEventListener('keydown', (e) => {
      // 编辑输入框中不处理快捷键
      if (document.activeElement?.classList.contains('inline-edit')) {
        return;
      }

      switch (e.key) {
        case 'Tab':
          e.preventDefault();
          APP.addChild();
          break;
        case 'Enter':
          e.preventDefault();
          APP.addSibling(false);
          break;
        case 'Delete':
        case 'Backspace':
          if (this.selectedId && this.selectedId !== APP.mindmap?.root?.id) {
            e.preventDefault();
            APP.deleteNode();
          }
          break;
        case 'F2':
          e.preventDefault();
          if (this.selectedId) APP._startEdit(this.selectedId);
          break;
        case 'ArrowUp':
          if (e.altKey) { e.preventDefault(); APP.reorderNode('up'); }
          break;
        case 'ArrowDown':
          if (e.altKey) { e.preventDefault(); APP.reorderNode('down'); }
          break;
      }

      // Shift+Enter
      if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        APP.addSibling(true);
      }
      // Ctrl+Enter
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        APP.addParent();
      }
    });

    /* ══════ 滚轮缩放 ══════ */

    wrapper.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = wrapper.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const delta = -e.deltaY * 0.001;
      const factor = 1 + Math.min(Math.max(delta, -0.3), 0.3);
      const newScale = Math.min(Math.max(this.scale * factor, 0.1), 5);
      this.tx = mx - (mx - this.tx) * (newScale / this.scale);
      this.ty = my - (my - this.ty) * (newScale / this.scale);
      this.scale = newScale;
      this._applyTransform();
    }, { passive: false });

    /* ══════ Touch 支持 ══════ */

    let touches = [];
    let lastDist = 0;
    wrapper.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this._isPanning = true;
        this._panStartX = e.touches[0].clientX;
        this._panStartY = e.touches[0].clientY;
        this._panStartTx = this.tx;
        this._panStartTy = this.ty;
      } else if (e.touches.length === 2) {
        this._isPanning = false;
        touches = [e.touches[0], e.touches[1]];
        lastDist = Math.hypot(
          touches[0].clientX - touches[1].clientX,
          touches[0].clientY - touches[1].clientY
        );
      }
    }, { passive: true });
    wrapper.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && this._isPanning) {
        this.tx = this._panStartTx + (e.touches[0].clientX - this._panStartX);
        this.ty = this._panStartTy + (e.touches[0].clientY - this._panStartY);
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
      this._isPanning = false;
    }, { passive: true });
  },

  /* ══════ 选中 ══════ */

  select(nodeId) {
    this.deselect();
    this.selectedId = nodeId;
    const $g = document.querySelector(`.node-group[data-node-id="${nodeId}"]`);
    if ($g) $g.classList.add('selected');
    if (this.onSelect) this.onSelect(nodeId);
  },

  deselect() {
    if (this.selectedId) {
      const $old = document.querySelector(`.node-group[data-node-id="${this.selectedId}"]`);
      if ($old) $old.classList.remove('selected');
      this.selectedId = null;
      if (this.onDeselect) this.onDeselect();
    }
  },

  /* ══════ 视图 ══════ */

  fitView() {
    this.scale = 1;
    this.tx = 80;
    this.ty = 60;
    this._applyTransform();
  },

  _applyTransform() {
    const $vp = document.getElementById('viewport');
    $vp.setAttribute('transform', `translate(${this.tx}, ${this.ty}) scale(${this.scale})`);
  },

  /* ══════ 拖拽 ══════ */

  _startDrag(e) {
    const wrapper = document.getElementById('canvas-wrapper');
    wrapper.classList.add('dragging');

    // 创建 ghost 元素
    const $g = document.querySelector(`.node-group[data-node-id="${this._dragNodeId}"]`);
    if (!$g) return;
    const $rect = $g.querySelector('.node-rect');
    const rect = $rect.getBoundingClientRect();

    const ghost = document.createElement('div');
    ghost.className = 'drag-ghost';
    ghost.style.left = rect.left + 'px';
    ghost.style.top = rect.top + 'px';
    ghost.style.width = rect.width + 'px';
    ghost.style.height = rect.height + 'px';
    ghost.textContent = $g.querySelector('.node-text')?.textContent || '';
    document.body.appendChild(ghost);
    this._dragGhost = ghost;

    // 高亮原节点
    $g.classList.add('dragging');
  },

  _moveDrag(e) {
    if (this._dragGhost) {
      this._dragGhost.style.left = (e.clientX - parseFloat(this._dragGhost.offsetWidth) / 2) + 'px';
      this._dragGhost.style.top = (e.clientY - parseFloat(this._dragGhost.offsetHeight) / 2) + 'px';
    }

    // 检测 drop target
    const wrapper = document.getElementById('canvas-wrapper');
    const rect = wrapper.getBoundingClientRect();
    const svgX = (e.clientX - rect.left - this.tx) / this.scale;
    const svgY = (e.clientY - rect.top - this.ty) / this.scale;

    // 清除之前的 high light
    document.querySelectorAll('.node-group.drop-target').forEach(el => el.classList.remove('drop-target'));

    // 找鼠标下的节点
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const $g = el?.closest('.node-group');
    if ($g && $g.dataset.nodeId !== this._dragNodeId) {
      $g.classList.add('drop-target');
      this._dropTargetId = $g.dataset.nodeId;
    } else {
      this._dropTargetId = null;
    }
  },

  _endDrag(e) {
    const wrapper = document.getElementById('canvas-wrapper');
    wrapper.classList.remove('dragging');

    // 清除 ghost
    if (this._dragGhost) {
      document.body.removeChild(this._dragGhost);
      this._dragGhost = null;
    }

    // 清除高亮
    document.querySelectorAll('.node-group.dragging').forEach(el => el.classList.remove('dragging'));
    document.querySelectorAll('.node-group.drop-target').forEach(el => el.classList.remove('drop-target'));

    // 触发 drop
    if (this._dragNodeId && this._dropTargetId && this._dropTargetId !== this._dragNodeId) {
      if (this.onNodeDrop) this.onNodeDrop(this._dragNodeId, this._dropTargetId);
    }
    this._dragNodeId = null;
    this._dropTargetId = null;
  },
};
