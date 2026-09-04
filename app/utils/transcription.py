from typing import Tuple


class TranscriptionModel:
    """Lazy-loads OpenAI Whisper for Urdu speech-to-text.

    The model is loaded on first use to keep API startup fast when
    transcription is not needed. Falls back to a stub if Whisper is not
    installed.
    """

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self.device = None

    def _load(self):
        if self.model is not None:
            return
        try:
            import torch
            import whisper

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model(self.model_name, device=self.device)
        except ImportError:
            print("openai-whisper not installed. Install with: pip install openai-whisper")
        except Exception as exc:
            print(f"Could not load Whisper model: {exc}")

    @property
    def is_loaded(self) -> bool:
        if self.model is None:
            self._load()
        return self.model is not None

    def transcribe(self, audio_path: str) -> Tuple[str, float]:
        """Transcribe audio file. Returns (text, speech_confidence)."""
        if not self.is_loaded:
            return "", 0.0

        result = self.model.transcribe(audio_path, language="ur")
        text = result.get("text", "").strip()
        no_speech = result.get("no_speech_prob", 1.0)
        confidence = round(1.0 - no_speech, 2)
        return text, confidence


_whisper_model = None


def transcribe_audio(file) -> str:
    """Transcribe from an uploaded file-like object (FastAPI compat)."""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = TranscriptionModel()

    import tempfile
    import os

    suffix = getattr(file, "filename", "audio.wav")
    ext = os.path.splitext(suffix)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        text, _ = _whisper_model.transcribe(tmp_path)
        return text
    finally:
        os.unlink(tmp_path)


def transcribe_audio_path(audio_path: str) -> Tuple[str, float]:
    """Transcribe from a file path (Gradio compat). Returns (text, confidence)."""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = TranscriptionModel()
    return _whisper_model.transcribe(audio_path)
