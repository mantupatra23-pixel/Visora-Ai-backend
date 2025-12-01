# tasks/physics_tasks.py
from celery import Celery
import os, subprocess, shlex
from pathlib import Path
import json

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('physics_tasks', broker=BROKER, backend=BROKER)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
SCRIPT = str(Path.cwd() / "blender_scripts" / "physics_worker.py")

@app.task(bind=True, time_limit=36000)
def run_physics_job(self, job_file, out_prefix):
    try:
        cmd = f"{BLENDER_BIN} --background --python {shlex.quote(SCRIPT)} -- {shlex.quote(job_file)} {shlex.quote(out_prefix)}"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=18000)
        return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}
