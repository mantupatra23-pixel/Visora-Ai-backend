# tasks/voice2anim_tasks.py
from celery import Celery
import os
app = Celery('v2a', broker=os.getenv("CELERY_BROKER","redis://redis:6379/0"))

@app.task(bind=True, time_limit=36000)
def run_v2a(self, wav_path, profile, mode, out_name):
    from services.voice2anim import run_voice2anim_pipeline
    return run_voice2anim_pipeline(wav_path, profile=profile, mode=mode, out_name=out_name)
