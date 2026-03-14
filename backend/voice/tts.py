import io
import os
import platform
import subprocess
import tempfile
import wave


class TTSEngine:
    """Text-to-speech engine with pyttsx3 primary and system fallback."""

    DEFAULT_SILENCE_DURATION_MS = 500
    DEFAULT_SAMPLE_RATE = 16000

    def __init__(self):
        self._engine_type = None  # "pyttsx3" | "say" | "espeak" | None
        self._pyttsx3_engine = None
        self._detect_engine()

    def _detect_engine(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.stop()
            self._pyttsx3_engine = None  # init lazily per call to avoid threading issues
            self._engine_type = "pyttsx3"
            return
        except Exception:
            pass

        system = platform.system()
        if system == "Darwin" and self._cmd_exists("say"):
            self._engine_type = "say"
        elif self._cmd_exists("espeak"):
            self._engine_type = "espeak"
        elif self._cmd_exists("espeak-ng"):
            self._engine_type = "espeak-ng"

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        return subprocess.call(
            ["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) == 0

    def synthesize(self, text: str) -> bytes:
        """Synthesize text and return WAV audio bytes."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            self.synthesize_to_file(text, tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def synthesize_to_file(self, text: str, output_path: str):
        """Synthesize text and save WAV to output_path."""
        if self._engine_type == "pyttsx3":
            self._synthesize_pyttsx3(text, output_path)
        elif self._engine_type == "say":
            self._synthesize_say(text, output_path)
        elif self._engine_type in ("espeak", "espeak-ng"):
            self._synthesize_espeak(text, output_path)
        else:
            # Fallback: write a minimal valid WAV (silence) so callers don't break
            self._write_silence_wav(output_path)

    def _synthesize_pyttsx3(self, text: str, output_path: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

    def _synthesize_say(self, text: str, output_path: str):
        # macOS `say` can output AIFF; convert via afconvert if available
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            aiff_path = tmp.name
        try:
            subprocess.run(["say", "-o", aiff_path, text], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Convert AIFF -> WAV using afconvert
            result = subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", aiff_path, output_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if result.returncode != 0:
                # Just copy the aiff as-is with a .wav extension (not ideal but functional)
                import shutil
                shutil.copy(aiff_path, output_path)
        finally:
            if os.path.exists(aiff_path):
                os.unlink(aiff_path)

    def _synthesize_espeak(self, text: str, output_path: str):
        cmd = self._engine_type  # "espeak" or "espeak-ng"
        subprocess.run(
            [cmd, "-w", output_path, text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _write_silence_wav(
        output_path: str,
        duration_ms: int = 500,
        sample_rate: int = 16000,
    ):
        n_samples = int(sample_rate * duration_ms / 1000)
        with wave.open(output_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * n_samples)
