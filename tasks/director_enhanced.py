# tasks/director_enhanced.py
from celery import Celery
import os, json, shlex, subprocess, uuid
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('director_enh', broker=BROKER, backend=BROKER)

SCRIPT = str(Path.cwd() / "blender_scripts" / "camera_choreographer.py")  # we'll call enhanced mode via env var or args
ENH_SCRIPT = str(Path.cwd() / "blender_scripts" / "camera_choreographer_enhanced.py")

@app.task(bind=True, time_limit=36000)
def run_director_enhanced(self, jobfile, out_prefix, blender_bin="blender"):
    """
    This task runs the enhanced Blender choreographer (camera_choreographer_enhanced.py)
    which imports all the helper modules (visibility, multi_reframe, spline moves).
    """
    cmd = f"{shlex.quote(blender_bin)} --background --python {shlex.quote(ENH_SCRIPT)} -- {shlex.quote(jobfile)} {shlex.quote(out_prefix)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok": p.returncode==0, "stdout": p.stdout[:2000], "stderr": p.stderr[:2000], "out_prefix": out_prefix}
