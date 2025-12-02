# tasks/romantic_tasks.py
from celery import Celery
import subprocess, shlex, os, json
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('romantic', broker=BROKER, backend=BROKER)

@app.task
def romantic_pipeline(jobfile):
    out = Path("jobs/romantic") / (Path(jobfile).stem + "_out")
    out.mkdir(parents=True, exist_ok=True)
    script = "blender_scripts/romantic_baker.py"
    cmd = f"{BLENDER_BIN} --background --python {script} -- {jobfile} {out}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok":p.returncode==0, "outdir": str(out)}
