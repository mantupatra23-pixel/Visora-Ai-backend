# tasks/openpose_tasks.py
from celery import Celery
from services.openpose_wrapper import run_openpose_on_video
import os
app = Celery('mocap_tasks', broker=os.getenv("CELERY_BROKER_URI","redis://redis:6379/0"))

@app.task(bind=True, time_limit=36000)
def openpose_extract(self, video_path, out_json_dir=None, body=25):
    return run_openpose_on_video(video_path, out_json_dir, body)
