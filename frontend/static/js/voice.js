/**
 * voice.js – Voice recording and CAAL-style waveform visualisation
 * Uses vertical animated bars driven by audio frequency data.
 * requestAnimationFrame for all rendering; transform/opacity only for GPU.
 */

const MIN_RECORDING_SIZE_BYTES = 1000;

// Visual constants
const NUM_BARS  = 40;
const BAR_GAP   = 3;
const BAR_RADIUS = 2;

class VoiceRecorder {
  constructor({ onTranscription, onStatusChange } = {}) {
    this.onTranscription = onTranscription || (() => {});
    this.onStatusChange  = onStatusChange  || (() => {});

    this._mediaRecorder = null;
    this._audioContext  = null;
    this._analyser      = null;
    this._source        = null;
    this._animFrame     = null;
    this._idleAnimFrame = null;
    this._chunks        = [];
    this._stream        = null;
    this.isRecording    = false;

    // Smoothed bar heights for fluid animation
    this._smoothed = new Float32Array(NUM_BARS).fill(0);

    this.canvas    = document.getElementById('waveformCanvas');
    this.ctx       = this.canvas ? this.canvas.getContext('2d') : null;

    this._setupCanvas();
    this._startIdleAnimation();
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  async toggle() {
    if (this.isRecording) this.stop();
    else await this.start();
  }

  async start() {
    if (this.isRecording) return;
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (err) {
      this.onStatusChange('error', `Microphone access denied: ${err.message}`);
      return;
    }

    this._stopIdleAnimation();
    this._setupAnalyser(this._stream);

    this._chunks = [];
    this._mediaRecorder = new MediaRecorder(this._stream);
    this._mediaRecorder.addEventListener('dataavailable', e => {
      if (e.data.size > 0) this._chunks.push(e.data);
    });
    this._mediaRecorder.addEventListener('stop', () => this._onRecordingStop());
    this._mediaRecorder.start();

    this.isRecording = true;
    this.onStatusChange('recording');
    this._startRecordingAnimation();
  }

  stop() {
    if (!this.isRecording) return;
    this.isRecording = false;
    if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
      this._mediaRecorder.stop();
    }
    if (this._stream) {
      this._stream.getTracks().forEach(t => t.stop());
      this._stream = null;
    }
    if (this._animFrame) {
      cancelAnimationFrame(this._animFrame);
      this._animFrame = null;
    }
    this.onStatusChange('processing');
    this._startIdleAnimation();
  }

  // ── Private ─────────────────────────────────────────────────────────────────

  _setupCanvas() {
    if (!this.canvas || !this.ctx) return;
    const dpr = window.devicePixelRatio || 1;
    // Logical dimensions from CSS
    this._cw = 480;
    this._ch = 160;
    this.canvas.width  = this._cw * dpr;
    this.canvas.height = this._ch * dpr;
    this.ctx.scale(dpr, dpr);
  }

  _setupAnalyser(stream) {
    try {
      this._audioContext = new AudioContext();
      this._analyser = this._audioContext.createAnalyser();
      this._analyser.fftSize = 128;  // frequencyBinCount = fftSize/2 = 64 bins — lightweight
      this._source = this._audioContext.createMediaStreamSource(stream);
      this._source.connect(this._analyser);
    } catch {
      this._analyser = null;
    }
  }

  async _onRecordingStop() {
    const blob = new Blob(this._chunks, { type: 'audio/webm' });
    this._chunks = [];

    if (blob.size < MIN_RECORDING_SIZE_BYTES) {
      this.onStatusChange('idle');
      return;
    }

    const formData = new FormData();
    formData.append('file', blob, 'recording.webm');

    try {
      const resp = await fetch('/api/voice/transcribe', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const text = (data.text || '').trim();
      if (text) this.onTranscription(text);
    } catch (err) {
      console.error('Transcription failed:', err);
    } finally {
      this.onStatusChange('idle');
    }
  }

  // ── Waveform animations ──────────────────────────────────────────────────────

  /** Gentle breathing animation while idle / processing. */
  _startIdleAnimation() {
    const draw = () => {
      this._drawIdleBars();
      this._idleAnimFrame = requestAnimationFrame(draw);
    };
    draw();
  }

  _stopIdleAnimation() {
    if (this._idleAnimFrame) {
      cancelAnimationFrame(this._idleAnimFrame);
      this._idleAnimFrame = null;
    }
  }

  _drawIdleBars() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const W = this._cw, H = this._ch;
    const t = performance.now() / 1000;
    ctx.clearRect(0, 0, W, H);

    const barW = (W - BAR_GAP * (NUM_BARS - 1)) / NUM_BARS;

    for (let i = 0; i < NUM_BARS; i++) {
      const phase = (i / NUM_BARS) * Math.PI * 4;
      const wave  = Math.sin(t * 0.9 + phase) * 0.5 + 0.5;
      const amp   = 0.03 + wave * 0.07;  // 3% – 10% of height
      const barH  = Math.max(2, amp * H);
      const x     = i * (barW + BAR_GAP);
      const y     = (H - barH) / 2;
      const alpha = 0.1 + wave * 0.12;

      ctx.fillStyle = `rgba(0,212,255,${alpha.toFixed(3)})`;
      this._roundedRect(ctx, x, y, barW, barH, BAR_RADIUS);
      ctx.fill();
    }
  }

  /** Frequency-driven bar animation while recording. */
  _startRecordingAnimation() {
    const bufLen  = this._analyser ? this._analyser.frequencyBinCount : NUM_BARS;
    const freqData = new Uint8Array(bufLen);
    const SMOOTH  = 0.75;  // smoothing factor (0 = none, 1 = full hold)

    const draw = () => {
      if (!this.isRecording) return;
      this._animFrame = requestAnimationFrame(draw);

      const ctx = this.ctx;
      if (!ctx) return;
      const W = this._cw, H = this._ch;
      ctx.clearRect(0, 0, W, H);

      if (this._analyser) {
        this._analyser.getByteFrequencyData(freqData);
      }

      const barW = (W - BAR_GAP * (NUM_BARS - 1)) / NUM_BARS;

      for (let i = 0; i < NUM_BARS; i++) {
        const idx   = this._analyser
          ? Math.floor(i * bufLen / NUM_BARS)
          : i;
        const raw   = this._analyser ? freqData[idx] / 255 : 0;
        // Quadratic curve for better visual contrast
        const target = Math.max(0.04, raw * raw * 0.92);
        this._smoothed[i] = SMOOTH * this._smoothed[i] + (1 - SMOOTH) * target;

        const amp  = this._smoothed[i];
        const barH = Math.max(2, amp * H);
        const x    = i * (barW + BAR_GAP);
        const y    = (H - barH) / 2;
        const alpha = 0.35 + amp * 0.65;

        ctx.fillStyle = `rgba(0,212,255,${alpha.toFixed(3)})`;
        this._roundedRect(ctx, x, y, barW, barH, BAR_RADIUS);
        ctx.fill();
      }
    };

    draw();
  }

  /** Draw rounded-rectangle path (reusable). */
  _roundedRect(ctx, x, y, w, h, r) {
    if (h < r * 2) r = h / 2;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.arcTo(x + w, y,     x + w, y + r,     r);
    ctx.lineTo(x + w, y + h - r);
    ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
    ctx.lineTo(x + r, y + h);
    ctx.arcTo(x,     y + h, x,     y + h - r, r);
    ctx.lineTo(x,     y + r);
    ctx.arcTo(x,     y,     x + r, y,         r);
    ctx.closePath();
  }
}
