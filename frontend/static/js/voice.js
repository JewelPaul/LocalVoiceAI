/**
 * voice.js – Voice recording and waveform visualisation
 */

const MIN_RECORDING_SIZE_BYTES = 1000;
class VoiceRecorder {
  constructor({ onTranscription, onStatusChange } = {}) {
    this.onTranscription = onTranscription || (() => {});
    this.onStatusChange  = onStatusChange  || (() => {});

    this._mediaRecorder = null;
    this._audioContext  = null;
    this._analyser      = null;
    this._source        = null;
    this._animFrame     = null;
    this._chunks        = [];
    this._stream        = null;
    this.isRecording    = false;

    this.canvas  = document.getElementById('waveformCanvas');
    this.canvasCtx = this.canvas ? this.canvas.getContext('2d') : null;

    this._drawIdle();
  }

  // ── Public API ──────────────────────────────────────────

  async toggle() {
    if (this.isRecording) {
      this.stop();
    } else {
      await this.start();
    }
  }

  async start() {
    if (this.isRecording) return;
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (err) {
      this.onStatusChange('error', `Microphone access denied: ${err.message}`);
      return;
    }

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
    this._drawWaveform();
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
    this._drawIdle();
  }

  // ── Private ─────────────────────────────────────────────

  _setupAnalyser(stream) {
    try {
      this._audioContext = new AudioContext();
      this._analyser = this._audioContext.createAnalyser();
      this._analyser.fftSize = 256;
      this._source = this._audioContext.createMediaStreamSource(stream);
      this._source.connect(this._analyser);
    } catch (e) {
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
      if (text) {
        this.onTranscription(text);
      }
    } catch (err) {
      console.error('Transcription failed:', err);
    } finally {
      this.onStatusChange('idle');
    }
  }

  // ── Waveform drawing ────────────────────────────────────

  _drawWaveform() {
    if (!this.canvasCtx || !this._analyser) {
      this._animFrame = requestAnimationFrame(() => this._drawWaveform());
      return;
    }

    const draw = () => {
      if (!this.isRecording) return;
      this._animFrame = requestAnimationFrame(draw);

      const bufferLength = this._analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      this._analyser.getByteTimeDomainData(dataArray);

      const { width, height } = this.canvas;
      this.canvasCtx.clearRect(0, 0, width, height);
      this.canvasCtx.lineWidth = 2;
      this.canvasCtx.strokeStyle = '#00d4ff';
      this.canvasCtx.beginPath();

      const sliceWidth = width / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * height) / 2;
        if (i === 0) this.canvasCtx.moveTo(x, y);
        else this.canvasCtx.lineTo(x, y);
        x += sliceWidth;
      }
      this.canvasCtx.lineTo(width, height / 2);
      this.canvasCtx.stroke();
    };

    draw();
  }

  _drawIdle() {
    if (!this.canvasCtx) return;
    const { width, height } = this.canvas;
    this.canvasCtx.clearRect(0, 0, width, height);
    this.canvasCtx.lineWidth = 1.5;
    this.canvasCtx.strokeStyle = 'rgba(136,136,170,0.3)';
    this.canvasCtx.beginPath();
    this.canvasCtx.moveTo(0, height / 2);
    this.canvasCtx.lineTo(width, height / 2);
    this.canvasCtx.stroke();
  }
}
