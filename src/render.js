/**
 * Chart rendering.
 *
 * The chart is drawn in inches: a stitch is 1/stitch-gauge wide and
 * 1/row-gauge tall, so the drawing has the proportions of the finished fabric
 * rather than of a square grid. Rounds are centred on each other, which makes
 * the crown decreases show up as a taper.
 *
 * Stitch 0 of every round is drawn at the right-hand edge and the round runs
 * leftwards, matching the way knitting charts are read.
 */

const SECTION_LABELS = { cuff: 'Cuff', body: 'Body', crown: 'Crown' };

export class ChartView {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.options = {
      colorMC: '#f4f1ea',
      colorCC: '#1f2933',
      background: '#ffffff',
      gridColor: 'rgba(31, 41, 51, 0.18)',
      accent: '#b4573a',
      textColor: '#5c6672',
      showGrid: true,
      showSections: true,
      showGlyphs: true,
      ...options,
    };
    this.plan = null;
    this.layout = null;
    this.camera = { x: 0, y: 0, scale: 40 };
    this.state = null;
    this.onPaint = null;
    this.paintMode = 'draw'; // 'draw' | 'pan'
    this._pointer = null;
    this._lastCell = -1;
    this._paintValue = 1;
    this._attach();
  }

  setPlan(plan, layout) {
    const first = !this.plan;
    this.plan = plan;
    this.layout = layout;
    this.cellW = 1 / plan.params.stitchGauge;
    this.cellH = 1 / plan.params.rowGauge;
    if (first) this.fit();
  }

  setState(state) {
    this.state = state;
  }

  setOptions(options) {
    Object.assign(this.options, options);
  }

  /* ---------------------------------------------------------------- camera */

  bounds() {
    let maxWidth = 0;
    for (let r = 0; r < this.layout.rowCount; r += 1) {
      maxWidth = Math.max(maxWidth, this.layout.widths[r]);
    }
    const halfW = (maxWidth / 2) * this.cellW;
    return {
      minX: -halfW,
      maxX: halfW,
      minY: 0,
      maxY: this.layout.rowCount * this.cellH,
    };
  }

  fit(padding = 1.08) {
    if (!this.layout) return;
    const { width, height } = this.size();
    this.userAdjusted = false;
    this._fittedTo = `${Math.round(width)}x${Math.round(height)}`;
    const b = this.bounds();
    const w = Math.max(1e-6, b.maxX - b.minX) * padding;
    const h = Math.max(1e-6, b.maxY - b.minY) * padding;
    this.camera.scale = Math.max(2, Math.min(width / w, height / h));
    this.camera.x = (b.minX + b.maxX) / 2;
    this.camera.y = (b.minY + b.maxY) / 2;
  }

  size() {
    if (this._sizeOverride) return this._sizeOverride;
    const rect = this.canvas.getBoundingClientRect();
    return { width: rect.width || this.canvas.width, height: rect.height || this.canvas.height };
  }

  worldToScreen(x, y) {
    const { width, height } = this.size();
    return {
      x: (x - this.camera.x) * this.camera.scale + width / 2,
      y: height / 2 - (y - this.camera.y) * this.camera.scale,
    };
  }

  screenToWorld(sx, sy) {
    const { width, height } = this.size();
    return {
      x: (sx - width / 2) / this.camera.scale + this.camera.x,
      y: this.camera.y - (sy - height / 2) / this.camera.scale,
    };
  }

  /** Which cell sits under a canvas coordinate, or -1. */
  cellAt(sx, sy) {
    if (!this.layout) return -1;
    const { x, y } = this.screenToWorld(sx, sy);
    const row = Math.floor(y / this.cellH);
    if (row < 0 || row >= this.layout.rowCount) return -1;
    const width = this.layout.widths[row];
    const stitch = Math.floor(width / 2 - x / this.cellW);
    if (stitch < 0 || stitch >= width) return -1;
    return this.layout.offsets[row] + stitch;
  }

  /* ----------------------------------------------------------------- input */

  _attach() {
    const canvas = this.canvas;

    canvas.addEventListener('contextmenu', (event) => event.preventDefault());

    canvas.addEventListener('pointerdown', (event) => {
      canvas.setPointerCapture(event.pointerId);
      const panning = this.paintMode === 'pan' || event.button !== 0 || event.shiftKey;
      this._pointer = { x: event.offsetX, y: event.offsetY, panning };
      if (!panning) {
        const cell = this.cellAt(event.offsetX, event.offsetY);
        if (cell >= 0 && this.state) {
          this._paintValue = this.state[cell] ? 0 : 1;
          this._lastCell = cell;
          if (this.onPaint) this.onPaint(cell, this._paintValue);
        }
      }
    });

    canvas.addEventListener('pointermove', (event) => {
      if (!this._pointer) return;
      if (this._pointer.panning) {
        const dx = event.offsetX - this._pointer.x;
        const dy = event.offsetY - this._pointer.y;
        this.userAdjusted = true;
        this.camera.x -= dx / this.camera.scale;
        this.camera.y += dy / this.camera.scale;
        this._pointer.x = event.offsetX;
        this._pointer.y = event.offsetY;
        this.requestDraw();
      } else {
        const cell = this.cellAt(event.offsetX, event.offsetY);
        if (cell >= 0 && cell !== this._lastCell) {
          this._lastCell = cell;
          if (this.onPaint) this.onPaint(cell, this._paintValue);
        }
      }
    });

    const endPointer = (event) => {
      if (this._pointer && canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }
      this._pointer = null;
      this._lastCell = -1;
    };
    canvas.addEventListener('pointerup', endPointer);
    canvas.addEventListener('pointercancel', endPointer);

    canvas.addEventListener(
      'wheel',
      (event) => {
        event.preventDefault();
        this.userAdjusted = true;
        const before = this.screenToWorld(event.offsetX, event.offsetY);
        const factor = Math.exp(-event.deltaY * 0.0015);
        this.camera.scale = Math.max(2, Math.min(4000, this.camera.scale * factor));
        const after = this.screenToWorld(event.offsetX, event.offsetY);
        this.camera.x += before.x - after.x;
        this.camera.y += before.y - after.y;
        this.requestDraw();
      },
      { passive: false },
    );
  }

  requestDraw() {
    if (this._frame) return;
    this._frame = requestAnimationFrame(() => {
      this._frame = null;
      this.draw();
    });
  }

  /* ---------------------------------------------------------------- drawing */

  resize() {
    const { width, height } = this.size();
    const dpr = typeof devicePixelRatio === 'number' ? devicePixelRatio : 1;
    this.canvas.width = Math.max(1, Math.round(width * dpr));
    this.canvas.height = Math.max(1, Math.round(height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  draw(targetCtx) {
    const ctx = targetCtx || this.ctx;
    if (!targetCtx) this.resize();
    let { width, height } = this.size();

    // The canvas has no size until the page has been laid out, and the window
    // can change shape later. Re-fit until the reader takes over the camera.
    if (!targetCtx && !this.userAdjusted && this._fittedTo !== `${Math.round(width)}x${Math.round(height)}`) {
      this.fit();
      ({ width, height } = this.size());
    }

    ctx.fillStyle = this.options.background;
    ctx.fillRect(0, 0, width, height);
    if (!this.layout || !this.state) return;

    const { widths, offsets, rowCount } = this.layout;
    const scale = this.camera.scale;
    const cellPx = this.cellW * scale;
    const rowPx = this.cellH * scale;
    const drawGlyphs = this.options.showGlyphs && cellPx > 9 && rowPx > 6;
    const drawGrid = this.options.showGrid && cellPx > 4 && rowPx > 4;

    for (let r = 0; r < rowCount; r += 1) {
      const yTop = this.worldToScreen(0, (r + 1) * this.cellH).y;
      if (yTop > height || yTop + rowPx < 0) continue;

      const width_ = widths[r];
      const base = offsets[r];
      const right = this.worldToScreen((width_ / 2) * this.cellW, 0).x;
      const left = right - width_ * cellPx;
      if (left > width || right < 0) continue;

      ctx.fillStyle = this.options.colorMC;
      ctx.fillRect(left, yTop, width_ * cellPx, rowPx + 0.5);

      ctx.fillStyle = this.options.colorCC;
      for (let i = 0; i < width_; i += 1) {
        if (!this.state[base + i]) continue;
        const x = right - (i + 1) * cellPx;
        if (x + cellPx < 0 || x > width) continue;
        ctx.fillRect(x, yTop, cellPx + 0.5, rowPx + 0.5);
      }

      if (drawGlyphs) {
        ctx.strokeStyle = 'rgba(120, 120, 120, 0.35)';
        ctx.lineWidth = Math.max(0.5, cellPx * 0.06);
        ctx.beginPath();
        for (let i = 0; i < width_; i += 1) {
          const x = right - (i + 1) * cellPx;
          if (x + cellPx < 0 || x > width) continue;
          ctx.moveTo(x + cellPx * 0.12, yTop + rowPx * 0.12);
          ctx.lineTo(x + cellPx * 0.5, yTop + rowPx * 0.88);
          ctx.lineTo(x + cellPx * 0.88, yTop + rowPx * 0.12);
        }
        ctx.stroke();
      } else if (drawGrid) {
        ctx.strokeStyle = this.options.gridColor;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        for (let i = 0; i <= width_; i += 1) {
          const x = right - i * cellPx;
          if (x < 0 || x > width) continue;
          ctx.moveTo(Math.round(x) + 0.5, yTop);
          ctx.lineTo(Math.round(x) + 0.5, yTop + rowPx);
        }
        ctx.stroke();
      }
    }

    if (drawGrid || drawGlyphs) this._drawRowSeparators(ctx, width, height);
    if (this.options.showSections) this._drawSections(ctx, width, height);
  }

  _drawRowSeparators(ctx, width, height) {
    const { widths, rowCount } = this.layout;
    ctx.strokeStyle = this.options.gridColor;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (let r = 0; r <= rowCount; r += 1) {
      const y = this.worldToScreen(0, r * this.cellH).y;
      if (y < 0 || y > height) continue;
      const w = widths[Math.min(r, rowCount - 1)];
      const right = this.worldToScreen((w / 2) * this.cellW, 0).x;
      const left = this.worldToScreen((-w / 2) * this.cellW, 0).x;
      ctx.moveTo(Math.max(0, left), Math.round(y) + 0.5);
      ctx.lineTo(Math.min(width, right), Math.round(y) + 0.5);
    }
    ctx.stroke();
  }

  _drawSections(ctx, width, height) {
    const rows = this.plan.rows;
    ctx.font = '12px ui-sans-serif, system-ui, sans-serif';
    ctx.textBaseline = 'middle';

    const marks = [];
    for (let r = 0; r < rows.length; r += 1) {
      const row = rows[r];
      const previous = rows[r - 1];
      if (!previous || previous.section !== row.section) {
        marks.push({ row: r, label: `${SECTION_LABELS[row.section]} · round ${r + 1} · ${row.width} sts` });
      } else if (row.kind === 'increase' || row.kind === 'turn' || row.kind === 'adjust') {
        marks.push({ row: r, label: `${row.kind} round · ${row.width} sts` });
      }
    }
    marks.push({ row: rows.length, label: `Draw up remaining ${rows[rows.length - 1].width} sts` });

    for (const mark of marks) {
      const y = this.worldToScreen(0, mark.row * this.cellH).y;
      if (y < -20 || y > height + 20) continue;
      const w = this.layout.widths[Math.min(mark.row, this.layout.rowCount - 1)];
      const left = this.worldToScreen((-w / 2) * this.cellW, 0).x;
      ctx.strokeStyle = this.options.accent;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(Math.max(0, left - 14), Math.round(y) + 0.5);
      ctx.lineTo(Math.min(width, this.worldToScreen((w / 2) * this.cellW, 0).x + 14), Math.round(y) + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
      this._label(ctx, mark.label, 10, Math.max(10, Math.min(height - 10, y - 9)), 'left', this.options.accent);
    }

    // Round numbers down the right-hand side.
    const rowPx = this.cellH * this.camera.scale;
    const stride = rowPx > 16 ? 5 : rowPx > 6 ? 10 : 25;
    for (let r = 0; r < rows.length; r += 1) {
      if ((r + 1) % stride !== 0) continue;
      const y = this.worldToScreen(0, (r + 0.5) * this.cellH).y;
      if (y < 0 || y > height) continue;
      this._label(ctx, String(r + 1), width - 8, y, 'right', this.options.textColor);
    }
  }

  /** Text on a plate, so labels stay readable over the chart. */
  _label(ctx, text, x, y, align, color) {
    const padding = 4;
    const metrics = ctx.measureText(text);
    const w = metrics.width + padding * 2;
    const left = align === 'right' ? x - w + padding : x - padding;
    ctx.fillStyle = this.options.background;
    ctx.globalAlpha = 0.82;
    ctx.fillRect(left, y - 9, w, 18);
    ctx.globalAlpha = 1;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.fillText(text, x, y);
  }

  /** Render the current chart to a detached canvas, for PNG export. */
  toCanvas(pixelsPerInch = 120, padding = 24) {
    const b = this.bounds();
    const w = Math.ceil((b.maxX - b.minX) * pixelsPerInch) + padding * 2;
    const h = Math.ceil((b.maxY - b.minY) * pixelsPerInch) + padding * 2;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');

    const camera = { ...this.camera };
    this.camera = { x: (b.minX + b.maxX) / 2, y: (b.minY + b.maxY) / 2, scale: pixelsPerInch };
    this._sizeOverride = { width: w, height: h };
    try {
      this.draw(ctx);
    } finally {
      this._sizeOverride = null;
      this.camera = camera;
    }
    return canvas;
  }
}
