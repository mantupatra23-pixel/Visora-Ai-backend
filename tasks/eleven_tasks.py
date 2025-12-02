# tasks/eleven_tasks.py
from celery import Celery
import json, os
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('eleven', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def tts_task(self, text, voice_id=None, out_name=None, stability=None, similarity_boost=None):
    from services.elevenlabs_service import tts_generate
    return tts_generate(text, voice_id=voice_id, output_name=out_name, stability=stability, similarity_boost=similarity_boost)

@app.task(bind=True)
def clone_and_speak(self, sample_path, text_to_speak, voice_name=None, consent=False):
    from services.eleven_voice_clone import create_instant_clone, synthesize_clone_text
    r = create_instant_clone(sample_path, voice_name=voice_name, consent=consent)
    if not r.get("ok"):
        return r
    vid = r["voice_id"]
    return synthesize_clone_text(text_to_speak, vid, output_name=f"clone_{vid}_out")
