# tasks/compositor_worker.py
from celery import Celery, group
import os, subprocess, shlex, json
from pathlib import Path
import boto3

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('compositor', broker=BROKER, backend=BROKER)

BLENDER_SCRIPT = str(Path.cwd() / "blender_scripts" / "composite_passes_oidn.py")

@app.task(bind=True, time_limit=18000)
def render_frame_task(self, jobfile, frame, outdir):
    cmd = f"blender --background --python {shlex.quote(BLENDER_SCRIPT)} -- {shlex.quote(jobfile)} {shlex.quote(outdir)}"
    # The composite script currently loops frames; for parallelism: we could support a single-frame mode
    # For now call script with env var FRAME to instruct it to render single frame (modify script to read os.environ['FRAME'])
    env = os.environ.copy()
    env['FRAME'] = str(frame)
    p = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    return {"ok": p.returncode==0, "frame": frame, "stdout": p.stdout[:200], "stderr": p.stderr[:200]}

@app.task(bind=True)
def upload_to_s3(self, file_path, bucket, key, acl="private"):
    s3 = boto3.client('s3',
                      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                      region_name=os.getenv("AWS_REGION"))
    try:
        s3.upload_file(file_path, bucket, key, ExtraArgs={"ACL": acl})
        url = f"s3://{bucket}/{key}"
        return {"ok": True, "s3_url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}
