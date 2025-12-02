# tasks/director_tasks.py
from celery import Celery
import os, subprocess, shlex, json, time
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")  # make sure this env var points to blender binary on worker
app = Celery('director', broker=BROKER, backend=BROKER)

# Path to blender scripts folder (relative to project root)
SCRIPT_DIR = Path.cwd() / "blender_scripts"
DIRECTOR_SCRIPT = SCRIPT_DIR / "director_baker.py"  # expected blender script

@app.task(bind=True, time_limit=36000)
def run_director_job(self, jobfile_path: str):
    """
    Run director baker inside blender headless.
    jobfile_path: path to job json created by create_director_job
    Writes result manifest into out_dir/result.json and returns summary dict.
    """
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error": "jobfile_missing"}

    try:
        job = json.loads(jobf.read_text())
    except Exception as e:
        return {"ok": False, "error": "invalid_jobfile", "detail": str(e)}

    # compute out_dir (prefer existing key, else jobs/director/<jobid>_out)
    job_id = job.get("job_id") or job.get("id") or jobf.stem
    out_dir = Path(job.get("output_dir") or (Path("jobs/director") / (job_id + "_out")))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ensure Blender script exists
    if not DIRECTOR_SCRIPT.exists():
        # try alternate path inside scripts
        alt = Path("blender_scripts") / "director_baker.py"
        if alt.exists():
            script_path = alt
        else:
            return {"ok": False, "error": "missing_blender_script", "expected": str(DIRECTOR_SCRIPT)}
    else:
        script_path = DIRECTOR_SCRIPT

    # build command: blender --background --python director_baker.py -- <jobfile> <out_dir>
    cmd = f"{shlex.quote(BLENDER_BIN)} --background --python {shlex.quote(str(script_path))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"
    self.update_state(state="STARTED", meta={"cmd": cmd})

    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=36000)
        ok = proc.returncode == 0
        summary = {
            "ok": ok,
            "rc": proc.returncode,
            "stdout": proc.stdout[:10000],
            "stderr": proc.stderr[:10000],
            "cmd": cmd
        }
        # write result.json to out_dir
        (out_dir / "result.json").write_text(json.dumps(summary, indent=2))
        # also update job manifest (optional): write a status file next to original job
        try:
            job_result = {"job_id": job_id, "status": ("done" if ok else "failed"), "out_dir": str(out_dir)}
            (Path("jobs/director") / f"{job_id}.json").write_text(json.dumps(job_result, indent=2))
        except Exception:
            pass

        return summary
    except subprocess.TimeoutExpired as e:
        res = {"ok": False, "error": "timeout", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(res, indent=2))
        return res
    except Exception as e:
        res = {"ok": False, "error": "exception", "detail": str(e)}
        (out_dir / "result.json").write_text(json.dumps(res, indent=2))
        return res
