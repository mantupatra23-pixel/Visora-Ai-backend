# services/asr_service.py
"""
Simple ASR wrapper. Prefers OpenAI/whisper if available locally;
falls back to Vosk offline model if installed.
Produces: {"text": "...", "segments": [{"start":0.0,"end":1.2,"text":"..."}], "lang": "en"}
"""
import os, json, subprocess
from pathlib import Path

def transcribe_with_whisper(audio_path, lang=None, model="small"):
    try:
        import whisper
        m = whisper.load_model(model)
        res = m.transcribe(str(audio_path), language=lang, word_timestamps=True)
        segments = []
        for s in res.get("segments", []):
            segments.append({"start": s["start"], "end": s["end"], "text": s["text"].strip()})
        return {"ok": True, "text": res["text"].strip(), "segments": segments, "lang": res.get("language")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def transcribe_with_vosk(audio_path, model_dir="models/vosk-model-small"):
    try:
        from vosk import Model, KaldiRecognizer
        import wave, json
        wf = wave.open(str(audio_path), "rb")
        model = Model(model_dir)
        rec = KaldiRecognizer(model, wf.getframerate())
        segments = []
        text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                r = json.loads(rec.Result())
                text += " " + (r.get("text",""))
        r = json.loads(rec.FinalResult())
        text += " " + r.get("text","")
        return {"ok": True, "text": text.strip(), "segments": segments}
    except Exception as e:
        return {"ok": False, "error": str(e)}
