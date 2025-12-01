# tasks/lip_tasks.py
from celery import Celery
import os
app = Celery('lip', broker=os.getenv("CELERY_BROKER","redis://redis:6379/0"))

@app.task(bind=True)
def run_lip_job(self, image_path, audio_path, text, emotion, engine, out_name):
    from services.lip_emotion import create_lip_emotion_job
    return create_lip_emotion_job(image_path, audio_path=audio_path, text=text, emotion=emotion, engine=engine, out_name=out_name)
