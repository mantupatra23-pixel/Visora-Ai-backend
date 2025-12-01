# services/emotion_classifier.py
"""
Lightweight emotion classifier wrapper.
- audio_path -> predicts emotion using an audio emotion model (if installed)
- image_path -> predicts emotion using face-expression model (if installed)
- fallback: rule-based heuristics (pitch/loudness -> angry/happy)
Return: {"ok":True, "emotion":"happy", "score":0.83}
"""
import os, numpy as np, json
from pathlib import Path
import subprocess, shlex

ROOT = Path(".").resolve()
MODEL_DIR = ROOT / "models" / "emotion"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EMO_MODEL = MODEL_DIR / "audio_emotion.pt"   # optional
IMG_EMO_MODEL = MODEL_DIR / "img_emotion.pt"

def _fallback_audio_emotion(audio_path):
    # very rough heuristics: RMS loudness + spectral centroid
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=16000)
        rms = float(np.mean(librosa.feature.rms(y=y)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        if rms > 0.02 and centroid > 2000:
            return {"emotion":"angry","score":0.6}
        if rms > 0.01:
            return {"emotion":"happy","score":0.5}
        return {"emotion":"neutral","score":0.6}
    except Exception as e:
        return {"emotion":"neutral","score":0.5, "error": str(e)}

def classify_audio(audio_path: str):
    # if model exists, call torch inference script (user to place model)
    if AUDIO_EMO_MODEL.exists():
        # assume user has a small inference script at extern/emotion_audio/infer.py
        script = ROOT / "extern" / "emotion_audio" / "infer.py"
        if script.exists():
            cmd = f"python {shlex.quote(str(script))} --model {shlex.quote(str(AUDIO_EMO_MODEL))} --audio {shlex.quote(audio_path)}"
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            try:
                out = json.loads(p.stdout)
                return {"ok": True, **out}
            except Exception:
                return {"ok": False, "error": "model_failed", "stdout": p.stdout, "stderr": p.stderr}
    # fallback
    r = _fallback_audio_emotion(audio_path)
    r["ok"] = True
    return r

def classify_image(image_path: str):
    if IMG_EMO_MODEL.exists():
        script = ROOT / "extern" / "emotion_image" / "infer.py"
        if script.exists():
            cmd = f"python {shlex.quote(str(script))} --model {shlex.quote(str(IMG_EMO_MODEL))} --img {shlex.quote(image_path)}"
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            try:
                out = json.loads(p.stdout)
                return {"ok": True, **out}
            except Exception:
                return {"ok": False, "error": "model_failed", "stdout": p.stdout, "stderr": p.stderr}
    # fallback: neutral
    return {"ok": True, "emotion":"neutral","score":0.5}
