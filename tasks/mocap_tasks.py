from celery import Celery
import os
app = Celery('visora', broker=os.getenv("CELERY_BROKER","redis://redis:6379/0"))
@app.task(bind=True)
def run_openpose_task(self, video_path):
    from services.openpose_wrapper import run_openpose_on_video
    return run_openpose_on_video(video_path)
@app.task(bind=True)
def run_vp3d_task(self, json_dir):
    from services.lift3d import run_videopose3d
    return run_videopose3d(json_dir)
