# tasks/prop_tasks.py
from celery import Celery
import os, subprocess, shlex, json
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('prop', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_prop_job(self, jobfile_path: str):
    """
    Run a prop injection job using Blender headless.
    jobfile_path: absolute or relative path to job json saved by the API (contains job_id, model path, actions, out_prefix, etc.)
    The task will create an output folder jobs/props/<job_id>_out and write result.json there.
    """
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error": "jobfile_missing", "path": jobfile_path}

    try:
        job = json.loads(jobf.read_text())
    except Exception as e:
        return {"ok": False, "error": "invalid_jobfile", "detail": str(e)}

    out_dir = Path("jobs/props") / (job.get('job_id','unknown') + "_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    script = Path("blender_scripts") / "prop_attacher.py"
    if not script.exists():
        return {"ok": False, "error": "missing_blender_script", "script": str(script)}

    # build blender command
    cmd = f"{BLENDER_BIN} --background --python {shlex.quote(str(script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"

    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)  # 30 min timeout
        ok = proc.returncode == 0
        result = {
            "ok": ok,
            "stdout": proc.stdout[:4000],
            "stderr": proc.stderr[:4000],
            "rc": proc.returncode
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        return result
    except subprocess.TimeoutExpired as e:
        res = {"ok": False, "error": "timeout", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(res, indent=2))
        return res
    except Exception as e:
        res = {"ok": False, "error": "exception", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(res, indent=2))
        return res
