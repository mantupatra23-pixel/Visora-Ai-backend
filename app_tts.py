# app_tts.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Try Coqui
_HAS_COQUI = False
try:
    from TTS.api import TTS
    _HAS_COQUI = True
except Exception as e:
    print("Coqui TTS not available:", e)

# Try gTTS fallback
_HAS_GTTS = False
try:
    from gtts import gTTS
    _HAS_GTTS = True
except Exception as e:
    print("gTTS not available:", e)

class TTSReq(BaseModel):
    text: str
    filename: str | None = None

app = FastAPI(title="Visora TTS Server")

# Lazy-load Coqui model when first request comes
_coqui_model = None
_coqui_model_name = "tts_models/en/ljspeech/tacotron2-DDC"  # safe default (changeable)

def get_coqui_model():
    global _coqui_model
    if _coqui_model is None:
        print("Loading Coqui model:", _coqui_model_name)
        _coqui_model = TTS(_coqui_model_name)
    return _coqui_model

@app.get("/")
def home():
    return {"status": "Visora TTS Server running"}

@app.post("/tts/speak")
def speak(req: TTSReq):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    out_name = req.filename or f"tts_{abs(hash(text))%10_000_000}.mp3"
    out_path = OUT_DIR / out_name

    # Try Coqui first
    if _HAS_COQUI:
        try:
            model = get_coqui_model()
            # coqui saves file as given path (wav/mp3 depending on model)
            model.tts_to_file(text=text, file_path=str(out_path))
            return {"ok": True, "file": str(out_path)}
        except Exception as e:
            print("Coqui TTS error, falling back:", e)

    # Fallback: gTTS
    if _HAS_GTTS:
        try:
            tts = gTTS(text=text, lang="en")
            out_path = out_path.with_suffix(".mp3")
            tts.save(str(out_path))
            return {"ok": True, "file": str(out_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"gTTS failed: {e}")

    raise HTTPException(status_code=500, detail="No TTS backend available. Install TTS or gTTS.")
