/**
 * tools.js – Tool Activity Display
 * Renders tool execution status in the bottom-bar activity area.
 * Design: transparent log, CAAL-inspired minimal style.
 */
class ToolActivityDisplay {
  constructor() {
    this.currentToolEl = document.getElementById('currentTool');
    this.toolHistoryEl = document.getElementById('toolHistory');
    this._history = [];
  }

  static MAX_HISTORY_ENTRIES = 8;   // keep bottom bar uncluttered
  static MAX_ARG_DISPLAY_LENGTH = 36;

  /** Show animated "running" status for a tool. */
  onToolStart(tool, args) {
    const label = `${tool}(${this._formatArgs(args)})`;
    if (this.currentToolEl) {
      this.currentToolEl.className = 'current-tool-inline visible';
      this.currentToolEl.innerHTML =
        `<div class="spinner"></div><span>${this._escHtml(label)}</span>`;
    }
  }

  /** Show completion entry and clear the active tool. */
  onToolEnd(tool, status, durationMs, resultSummary) {
    if (status === 'success') {
      const seconds = (durationMs / 1000).toFixed(1);
      const summary = resultSummary ? String(resultSummary).substring(0, 60) : '';
      this._addEntry(
        `✓ ${tool} — ${seconds}s${summary ? '  ' + summary : ''}`,
        'success'
      );
    } else {
      const seconds = (durationMs / 1000).toFixed(1);
      this._addEntry(
        `✗ ${tool} — ${seconds}s · ${String(resultSummary || '').substring(0, 60)}`,
        'error'
      );
    }
    this._clearActive();
  }

  /** Show blocked entry. */
  onToolBlocked(tool, reason) {
    this._addEntry(`⊘ ${tool} — ${reason}`, 'blocked');
    this._clearActive();
  }

  // ── Private ──────────────────────────────────────────────────────────────────

  _formatArgs(args) {
    if (!args || typeof args !== 'object') return '';
    const MAX = ToolActivityDisplay.MAX_ARG_DISPLAY_LENGTH;
    const entries = Object.entries(args);
    const parts = entries.slice(0, 2).map(([k, v]) => {
      const s = String(v);
      const raw = s.substring(0, MAX);
      const val = typeof v === 'string'
        ? `"${raw}${s.length > MAX ? '…' : ''}"`
        : raw;
      return `${k}=${val}`;
    });
    if (entries.length > 2) parts.push('…');
    return parts.join(', ');
  }

  _addEntry(text, statusClass) {
    if (!this.toolHistoryEl) return;
    const div = document.createElement('div');
    div.className = `tool-entry ${statusClass}`;
    div.textContent = text;
    div.title = text;

    this._history.unshift(div);
    if (this._history.length > ToolActivityDisplay.MAX_HISTORY_ENTRIES) {
      const old = this._history.pop();
      old.remove();
    }
    this.toolHistoryEl.insertBefore(div, this.toolHistoryEl.firstChild);
  }

  _clearActive() {
    if (this.currentToolEl) {
      this.currentToolEl.className = 'current-tool-inline hidden';
      this.currentToolEl.innerHTML = '';
    }
  }

  _escHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

// Export global instance (used by app.js)
const toolDisplay = new ToolActivityDisplay();
