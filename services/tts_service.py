# services/tts_service.py
"""
Wrap common TTS engines:
- prefer coqui/tts if available (local), else pyttsx3 (offline), else fallback to cloud via edge provider.
Produces saved wav path.
"""
import os, uuid
from pathlib import Path

OUT_DIR = Path("assets/tts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def tts_coqui(text, lang="en", voice="random", out_name=None):
    try:
        from TTS.api import TTS
        model_name = "tts_models/multilingual/multi-dataset/your_tts"  # placeholder; choose installed model
        tts = TTS(model_name)
        out_file = OUT_DIR / (out_name or f"tts_{uuid.uuid4().hex}.wav")
        tts.tts_to_file(text=text, file_path=str(out_file))
        return {"ok": True, "path": str(out_file)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tts_pyttsx3(text, lang="en", voice=None, out_name=None):
    try:
        import pyttsx3, wave
        engine = pyttsx3.init()
        if voice:
            engine.setProperty('voice', voice)
        out_file = OUT_DIR / (out_name or f"tts_{uuid.uuid4().hex}.wav")
        engine.save_to_file(text, str(out_file))
        engine.runAndWait()
        return {"ok": True, "path": str(out_file)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
