# services/parallel_compositor.py
from tasks.compositor_worker import render_frame_task, upload_to_s3
from celery import group
import json, uuid
from pathlib import Path

def submit_parallel_job(jobfile, start_frame, end_frame, outdir, s3_bucket=None, s3_prefix=None):
    frames = list(range(start_frame, end_frame+1))
    # create group of tasks
    grp = group(render_frame_task.s(jobfile, f, outdir) for f in frames)
    result = grp.apply_async()
    # optionally chain upload tasks after each frame finishes (or a single archive upload)
    return {"ok": True, "task_group_id": result.id, "frames": len(frames)}
