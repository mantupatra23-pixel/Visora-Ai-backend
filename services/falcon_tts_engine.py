import os
from pathlib import Path

# Try to import Coqui TTS (TTS package). If not available, we'll fallback to gTTS.
try:
    from TTS.api import TTS  # coqui TTS
    _HAS_COQUI = True
except Exception:
    _HAS_COQUI = False

try:
    from gtts import gTTS
    _HAS_GTTS = True
except Exception:
    _HAS_GTTS = False

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

class TTSService:
    def __init__(self):
        self.mode = None
        self.coqui = None
        if _HAS_COQUI:
            try:
                # NOTE: change model_name if you want a specific Falcon-like TTS model.
                # This loads a default TTS model available in coqui. On first run it will download weights.
                model_name = "tts_models/en/ljspeech/tacotron2-DDC"  # safe default
                self.coqui = TTS(model_name)
                self.mode = "coqui"
            except Exception as e:
                print("Coqui TTS import OK but model load failed:", e)
                self.coqui = None

        if self.mode is None and _HAS_GTTS:
            self.mode = "gtts"

        if self.mode is None:
            print("No TTS backend available. Install 'TTS' or 'gTTS'.")

    def synthesize(self, text: str, out_filename: str = None) -> str:
        """
        Synthesizes text and saves to a file in static/outputs.
        Returns the relative path to the file.
        """
        if not text:
            raise ValueError("Empty text")

        out_filename = out_filename or f"tts_{abs(hash(text)) % (10**9)}.mp3"
        out_path = OUT_DIR / out_filename

        if self.mode == "coqui" and self.coqui is not None:
            try:
                # Coqui TTS's tts_to_file will produce a WAV/MP3 depending on model.
                self.coqui.tts_to_file(text=text, file_path=str(out_path))
                return str(out_path)
            except Exception as e:
                print("Coqui synthesis failed:", e)
                # fallback to gTTS below if available

        if self.mode == "gtts":
            if not _HAS_GTTS:
                raise RuntimeError("gTTS not installed")
            try:
                tts = gTTS(text=text, lang="en")
                # gTTS saves mp3
                out_path = out_path.with_suffix(".mp3")
                tts.save(str(out_path))
                return str(out_path)
            except Exception as e:
                raise RuntimeError(f"gTTS synthesis failed: {e}")

        raise RuntimeError("No usable TTS backend available.")
