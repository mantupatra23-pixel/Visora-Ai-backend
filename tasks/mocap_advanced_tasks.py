# tasks/mocap_advanced_tasks.py
from celery import Celery
import os, subprocess, shlex, json
from pathlib import Path
import time

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('mocap_adv', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_mocap_advanced(self, jobfile_path):
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error": "jobfile_missing"}
    job = json.loads(jobf.read_text())
    out_dir = Path("jobs/mocap") / (job['job_id'] + "_adv_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    baker = Path("blender_scripts") / "mocap_pro_baker.py"
    cmd = f"{BLENDER_BIN} --background --python {shlex.quote(str(baker))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
        ok = proc.returncode == 0
        res = {"ok": ok, "stdout": proc.stdout[:5000], "stderr": proc.stderr[:5000], "rc": proc.returncode}
        (out_dir / "result.json").write_text(json.dumps(res, indent=2))
        return res
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": "timeout", "detail": str(e)}
