import io
import os
import tempfile


class WhisperSTT:
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None
        self._use_faster = False

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            self._use_faster = True
        except ImportError:
            try:
                import whisper
                self._model = whisper.load_model(self.model_name)
                self._use_faster = False
            except ImportError:
                raise RuntimeError(
                    "Neither faster-whisper nor openai-whisper is installed. "
                    "Install one to enable speech-to-text."
                )

    def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe raw audio bytes. Returns transcript string."""
        self._load_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        try:
            return self._transcribe_path(tmp_path, language)
        finally:
            os.unlink(tmp_path)

    def transcribe_file(self, file_path: str, language: str = "en") -> str:
        """Transcribe an audio file at the given path."""
        self._load_model()
        return self._transcribe_path(file_path, language)

    def _transcribe_path(self, path: str, language: str = "en") -> str:
        if self._use_faster:
            segments, _ = self._model.transcribe(path, language=language)
            return " ".join(seg.text.strip() for seg in segments)
        else:
            result = self._model.transcribe(path, language=language)
            return result.get("text", "").strip()
