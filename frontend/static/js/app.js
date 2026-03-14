/**
 * app.js – Main application logic
 * Connects WebSocket, Chat, Voice, Tools, and Settings/Permissions.
 * Minimal voice-first UI: no progress bar, inline voice state display.
 */

const MAX_CONTEXT_MESSAGES = 20;

const state = {
  ws: null,
  wsReady: false,
  model: '',
  chatHistory: [],       // [{role, content}]
  pendingConfirmId: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const statusDot       = $('statusDot');
const statusText      = $('statusText');
const connectionDot   = $('connectionDot');
const modelSelect     = $('modelSelect');
const chatHistoryEl   = $('chatHistory');
const chatInput       = $('chatInput');
const sendBtn         = $('sendBtn');
const micBtn          = $('micBtn');
const voiceState      = $('voiceState');
const liveTranscription = $('liveTranscription');
const confirmModal    = $('confirmModal');
const confirmDesc     = $('confirmDescription');
const confirmDetails  = $('confirmToolDetails');
const confirmAllow    = $('confirmAllow');
const confirmAlways   = $('confirmAlways');
const confirmCancel   = $('confirmCancel');
const settingsBtn     = $('settingsBtn');
const settingsModal   = $('settingsModal');
const closeSettings   = $('closeSettings');
const permissionsList = $('permissionsList');

// ── Permission metadata ────────────────────────────────────────────────────────
const PERM_META = {
  files:        { icon: '📁', label: 'Files' },
  downloads:    { icon: '⬇', label: 'Downloads' },
  browser:      { icon: '🌐', label: 'Browser' },
  email:        { icon: '📧', label: 'Email' },
  ocr:          { icon: '🔍', label: 'OCR' },
  images:       { icon: '🖼', label: 'Images' },
  video:        { icon: '🎬', label: 'Video' },
  spreadsheets: { icon: '📊', label: 'Spreadsheets' },
};

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connectWS() {
  setStatus('connecting');
  const ws = new WebSocket(`ws://${location.host}/ws`);
  state.ws = ws;

  ws.onopen = () => {
    state.wsReady = true;
    setStatus('connected');
  };

  ws.onclose = () => {
    state.wsReady = false;
    setStatus('disconnected');
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => {
    setStatus('disconnected');
  };

  ws.onmessage = ev => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    handleServerMessage(msg);
  };
}

function handleServerMessage(msg) {
  switch (msg.type) {
    case 'status':
      updateOllamaStatus(msg);
      break;
    case 'chat':
      appendChatMsg('assistant', msg.message);
      setVoiceState('idle');
      setSendBusy(false);
      break;
    case 'tool_start':
      toolDisplay.onToolStart(msg.tool, msg.args);
      setVoiceState('thinking');
      break;
    case 'tool_end':
      toolDisplay.onToolEnd(msg.tool, msg.status, msg.duration_ms, msg.result_summary);
      break;
    case 'tool_blocked':
      toolDisplay.onToolBlocked(msg.tool, msg.reason);
      break;
    case 'tool_confirm':
      showConfirmModal(msg);
      break;
    case 'transcription':
      showLiveTranscription(msg.text);
      break;
    case 'error':
      appendChatMsg('assistant', `⚠ ${msg.message}`);
      setVoiceState('idle');
      setSendBusy(false);
      break;
  }
}

// ── Status helpers ────────────────────────────────────────────────────────────
function setStatus(s) {
  const cls = `status-dot ${s}`;
  statusDot.className = cls;
  connectionDot.className = `conn-dot ${s}`;
  statusText.textContent =
    s === 'connected'    ? 'Connected' :
    s === 'connecting'   ? 'Connecting…' :
    s === 'disconnected' ? 'Disconnected' : s;
}

function updateOllamaStatus(msg) {
  if (msg.ollama_connected) setStatus('connected');
  const models = msg.models || [];
  modelSelect.innerHTML = '';
  if (models.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No models';
    modelSelect.appendChild(opt);
  } else {
    models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      modelSelect.appendChild(opt);
    });
    state.model = models[0];
    modelSelect.value = state.model;
  }
}

// ── Voice state label ─────────────────────────────────────────────────────────
function setVoiceState(s, msg) {
  const label =
    s === 'recording'  ? 'Listening…' :
    s === 'processing' ? 'Processing…' :
    s === 'thinking'   ? 'Thinking…' :
    s === 'error'      ? (msg || 'Error') :
    'Tap microphone to speak';

  voiceState.textContent = label;
  voiceState.className   = `voice-state${s !== 'idle' ? ' ' + s : ''}`;
}

function showLiveTranscription(text) {
  liveTranscription.textContent = text || '';
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function sendMessage(text) {
  text = text.trim();
  if (!text) return;
  if (!state.wsReady) {
    appendChatMsg('assistant', '⚠ Not connected. Please wait…');
    return;
  }

  appendChatMsg('user', text);
  state.chatHistory.push({ role: 'user', content: text });

  const model = modelSelect.value || state.model || 'qwen2.5:7b';
  state.ws.send(JSON.stringify({
    type: 'chat',
    message: text,
    model,
    history: state.chatHistory.slice(-MAX_CONTEXT_MESSAGES),
  }));

  chatInput.value = '';
  setSendBusy(true);
  setVoiceState('thinking');
}

function appendChatMsg(role, content) {
  if (role === 'assistant') {
    state.chatHistory.push({ role: 'assistant', content });
  }

  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;

  const roleLabel = document.createElement('div');
  roleLabel.className = 'msg-role';
  roleLabel.textContent = role === 'user' ? 'You' : 'AI';

  const text = document.createElement('div');
  text.textContent = content;

  div.appendChild(roleLabel);
  div.appendChild(text);
  chatHistoryEl.appendChild(div);
  chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
}

function setSendBusy(busy) {
  sendBtn.disabled  = busy;
  chatInput.disabled = busy;
}

// ── Voice ─────────────────────────────────────────────────────────────────────
const recorder = new VoiceRecorder({
  onTranscription(text) {
    showLiveTranscription(text);
    sendMessage(text);
  },
  onStatusChange(status, msg) {
    micBtn.classList.toggle('recording', status === 'recording');
    setVoiceState(status, msg);
    if (status === 'idle') showLiveTranscription('');
  },
});

micBtn.addEventListener('click', () => recorder.toggle());

// ── Settings modal ────────────────────────────────────────────────────────────
settingsBtn.addEventListener('click', () => {
  settingsModal.classList.remove('hidden');
});
closeSettings.addEventListener('click', () => {
  settingsModal.classList.add('hidden');
});
settingsModal.addEventListener('click', e => {
  if (e.target === settingsModal) settingsModal.classList.add('hidden');
});

// ── Confirmation Modal ────────────────────────────────────────────────────────
function showConfirmModal(msg) {
  state.pendingConfirmId = msg.id;
  confirmDesc.textContent = 'The AI wants to perform a sensitive action:';
  confirmDetails.textContent =
    `Tool: ${msg.tool}\nArgs: ${JSON.stringify(msg.args, null, 2)}\n\n${msg.description || ''}`;
  confirmModal.classList.remove('hidden');
}

function hideConfirmModal() {
  confirmModal.classList.add('hidden');
  state.pendingConfirmId = null;
}

function sendConfirm(allowed, always) {
  if (!state.pendingConfirmId || !state.wsReady) return;
  state.ws.send(JSON.stringify({
    type: 'confirm',
    id: state.pendingConfirmId,
    allowed,
    always,
  }));
  hideConfirmModal();
}

confirmAllow.addEventListener('click',  () => sendConfirm(true, false));
confirmAlways.addEventListener('click', () => sendConfirm(true, true));
confirmCancel.addEventListener('click', () => {
  if (state.pendingConfirmId && state.wsReady) {
    state.ws.send(JSON.stringify({ type: 'cancel', id: state.pendingConfirmId }));
  }
  hideConfirmModal();
});
confirmModal.addEventListener('click', e => {
  if (e.target === confirmModal) {
    state.ws?.send(JSON.stringify({ type: 'cancel', id: state.pendingConfirmId }));
    hideConfirmModal();
  }
});

// ── Permissions ───────────────────────────────────────────────────────────────
async function loadPermissions() {
  try {
    const resp = await fetch('/api/permissions');
    if (!resp.ok) return;
    const perms = await resp.json();
    renderPermissions(perms);
  } catch (e) {
    console.warn('Could not load permissions:', e);
  }
}

function renderPermissions(perms) {
  permissionsList.innerHTML = '';
  for (const [key, enabled] of Object.entries(perms)) {
    const meta = PERM_META[key] || { icon: '🔧', label: key };
    const item = document.createElement('div');
    item.className = 'perm-item';
    item.innerHTML = `
      <span class="perm-label">${meta.icon} ${meta.label}</span>
      <label class="toggle-switch">
        <input type="checkbox" data-key="${key}" ${enabled ? 'checked' : ''} />
        <span class="toggle-slider"></span>
      </label>
    `;
    permissionsList.appendChild(item);
  }

  permissionsList.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.addEventListener('change', async () => {
      const key   = cb.dataset.key;
      const value = cb.checked;
      try {
        await fetch('/api/permissions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ permissions: { [key]: value } }),
        });
      } catch {
        cb.checked = !value; // revert on failure
      }
    });
  });
}

// ── Event listeners ───────────────────────────────────────────────────────────
sendBtn.addEventListener('click', () => sendMessage(chatInput.value));
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(chatInput.value);
  }
});
modelSelect.addEventListener('change', () => {
  state.model = modelSelect.value;
});

// ── Boot ──────────────────────────────────────────────────────────────────────
(async () => {
  connectWS();
  await loadPermissions();
})();
