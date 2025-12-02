# tasks/wav2lip_tasks.py
from celery import Celery
import json, os
from pathlib import Path
from services.wav2lip_service import prepare_job, run_wav2lip, merge_audio_video

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery("wav2lip", broker=BROKER, backend=BROKER)

@app.task(bind=True)
def wav2lip_job(self, jobfile: str, use_gan: bool = False):
    p = Path(jobfile)
    job = json.loads(p.read_text()) if p.exists() else None
    if not job:
        return {"ok": False, "error": "jobfile_missing"}

    job['status'] = "running"
    p.write_text(json.dumps(job))

    video = job['video']
    audio = job.get('audio')
    out_dir = Path(job['out_dir'])
    out_video_temp = str(out_dir / "lipsynced_temp.mp4")
    final_out = str(out_dir / "lipsynced_final.mp4")

    # if audio not provided, use original video's audio (inference script can handle audio arg)
    if not audio:
        # extract audio from video
        audio = str(out_dir / "extracted_audio.wav")
        cmd = f'ffmpeg -y -i "{video}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio}"'
        os.system(cmd)

    rc, logs = run_wav2lip(video, audio, out_video_temp, use_gan=use_gan)
    if rc != 0:
        job['status'] = "failed"
        job['error'] = logs[:4000]
        p.write_text(json.dumps(job))
        return {"ok": False, "error": "wav2lip_failed", "logs": logs}

    # Mux audio back properly (optional)
    rc2, logs2 = merge_audio_video(video, out_video_temp, final_out)
    job['status'] = "done"
    job['result'] = {"outfile": final_out}
    p.write_text(json.dumps(job))
    return {"ok": True, "outfile": final_out}
