# tasks/prop_tasks.py
from celery import Celery
import os, shlex, subprocess
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('prop_tasks', broker=BROKER, backend=BROKER)

BLENDER_BIN = os.getenv("BLENDER_BIN", "/opt/blender/blender")
SCRIPT = str(Path.cwd() / "blender_scripts" / "prop_injector_worker.py")

@app.task(bind=True, time_limit=36000)
def run_prop_inject(self, jobfile, out_prefix):
    """
    jobfile: absolute path to job json saved by services.prop_injector
    out_prefix: output prefix to write results
    """
    try:
        cmd = f"{shlex.quote(BLENDER_BIN)} --background --python {shlex.quote(SCRIPT)} -- {shlex.quote(jobfile)} {shlex.quote(out_prefix)}"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=18000)
        return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}
