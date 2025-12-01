# tasks/director_tasks.py
from celery import Celery
import os
from pathlib import Path
import shlex, subprocess

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('director', broker=BROKER, backend=BROKER)

SCRIPT = str(Path.cwd() / "blender_scripts" / "camera_choreographer.py")

@app.task(bind=True, time_limit=36000)
def run_director(self, jobfile, out_prefix, blender_bin="blender"):
    cmd = f"{shlex.quote(blender_bin)} --background --python {shlex.quote(SCRIPT)} -- {shlex.quote(jobfile)} {shlex.quote(out_prefix)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok": p.returncode==0, "stdout": p.stdout[:2000], "stderr": p.stderr[:2000], "out_prefix": out_prefix}
