# tasks/mocap_tasks.py
"""
Celery task to run mocap/baking jobs in headless Blender.
Writes output into jobs/mocap/<job_id>_out/result.json with log and status.
Environment:
 - CELERY_BROKER (optional) : redis://redis:6379/0
 - BLENDER_BIN (optional)   : path to blender executable (default 'blender')
"""
from celery import Celery
import os, json, subprocess, shlex, time
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('mocap', broker=BROKER, backend=BROKER)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")  # path to blender binary

@app.task(bind=True)
def run_mocap_job(self, jobfile_path: str, timeout_seconds: int = 3600):
    """
    jobfile_path: path to a JSON job file describing inputs (job must include 'job_id')
    timeout_seconds: max seconds to allow Blender run (default 1 hour)
    Returns dict: {"ok": bool, "log": {...}, "out_dir": str} or error dict.
    """
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error": "jobfile_missing", "path": str(jobfile_path)}

    try:
        job = json.loads(jobf.read_text())
    except Exception as e:
        return {"ok": False, "error": "jobfile_invalid_json", "detail": str(e)}

    job_id = job.get("job_id") or f"job_{int(time.time())}"
    out_dir = Path("jobs") / "mocap" / (job_id + "_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    # blender script to run (expects to exist in blender_scripts/)
    script = Path("blender_scripts") / "mocap_pro_baker.py"
    if not script.exists():
        (out_dir / "result.json").write_text(json.dumps({
            "ok": False,
            "error": "missing_blender_script",
            "script": str(script)
        }, indent=2))
        return {"ok": False, "error": "missing_blender_script", "script": str(script)}

    # build safe shell command
    cmd = f"{shlex.quote(BLENDER_BIN)} --background --python {shlex.quote(str(script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"

    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout_seconds)
        ok = proc.returncode == 0
        log = {
            "stdout": proc.stdout[-5000:],   # keep last chunk
            "stderr": proc.stderr[-5000:],   # keep last chunk
            "rc": proc.returncode
        }
        result = {"ok": ok, "log": log, "out_dir": str(out_dir)}
        # write result manifest
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        return result
    except subprocess.TimeoutExpired as e:
        result = {"ok": False, "error": "timeout", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        return result
    except Exception as e:
        result = {"ok": False, "error": "exception", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        return result
