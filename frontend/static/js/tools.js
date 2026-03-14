/**
 * tools.js – Tool Activity Display
 * Manages the currently-running indicator and scrollable tool history.
 */
class ToolActivityDisplay {
  constructor() {
    this.currentToolEl = document.getElementById('currentTool');
    this.toolHistoryEl = document.getElementById('toolHistory');
    this._history = [];
  }

  static MAX_HISTORY_ENTRIES = 50;
  static MAX_ARG_DISPLAY_LENGTH = 40;

  /** Show animated "running" status for a tool. */
  showToolRunning(toolName, args) {
    const argsStr = this._formatArgs(args);
    const label = `${toolName}(${argsStr})`;

    this.currentToolEl.className = 'current-tool running';
    this.currentToolEl.innerHTML = `
      <div class="spinner"></div>
      <span>${this._escHtml(label)}</span>
    `;
  }

  /** Show completion entry and clear the active tool. */
  showToolComplete(toolName, durationMs, result) {
    const argsStr = '';
    const seconds = (durationMs / 1000).toFixed(1);
    const summary = result ? String(result).substring(0, 80) : '';
    const entry = `✅ ${toolName}(${argsStr}) — ${seconds}s${summary ? ' · ' + summary : ''}`;

    this._addHistoryEntry(entry, 'success');
    this._clearActive();
  }

  /** Show error entry. */
  showToolError(toolName, durationMs, error) {
    const seconds = (durationMs / 1000).toFixed(1);
    const entry = `❌ ${toolName}() — ${seconds}s · ${String(error).substring(0, 80)}`;
    this._addHistoryEntry(entry, 'error');
    this._clearActive();
  }

  /** Show blocked entry. */
  showToolBlocked(toolName, reason) {
    const entry = `🚫 ${toolName}() — Blocked: ${reason}`;
    this._addHistoryEntry(entry, 'blocked');
    this._clearActive();
  }

  /** Called on tool_start message from server. */
  onToolStart(tool, args) {
    this.showToolRunning(tool, args);
  }

  /** Called on tool_end message from server. */
  onToolEnd(tool, status, durationMs, resultSummary) {
    if (status === 'success') {
      this.showToolComplete(tool, durationMs, resultSummary);
    } else {
      this.showToolError(tool, durationMs, resultSummary);
    }
  }

  /** Called on tool_blocked message from server. */
  onToolBlocked(tool, reason) {
    this.showToolBlocked(tool, reason);
  }

  // ── Private helpers ──

  _formatArgs(args) {
    if (!args || typeof args !== 'object') return '';
    const parts = Object.entries(args).map(([k, v]) => {
      const val = typeof v === 'string' ? `"${v.substring(0, ToolActivityDisplay.MAX_ARG_DISPLAY_LENGTH)}"` : JSON.stringify(v);
      return `${k}=${val}`;
    });
    return parts.slice(0, 2).join(', ');
  }

  _addHistoryEntry(text, statusClass) {
    const div = document.createElement('div');
    div.className = `tool-entry ${statusClass}`;
    div.textContent = text;
    div.title = text;

    this._history.unshift(div);
    // Keep max MAX_HISTORY_ENTRIES entries
    if (this._history.length > ToolActivityDisplay.MAX_HISTORY_ENTRIES) {
      const old = this._history.pop();
      old.remove();
    }

    // Prepend to history list
    this.toolHistoryEl.insertBefore(div, this.toolHistoryEl.firstChild);
  }

  _clearActive() {
    this.currentToolEl.className = 'current-tool idle';
    this.currentToolEl.innerHTML = '<span class="idle-text">No active tool</span>';
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
