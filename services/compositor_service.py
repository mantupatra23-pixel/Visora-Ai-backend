# services/compositor_service.py
import json, time, uuid
from pathlib import Path

JOBS = Path("jobs/vfx")
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def make_vfx_job(plate_path: str, reference_path: str | None = None, options: dict | None = None):
    job_id = f"vfx_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "plate": plate_path,
        "reference": reference_path,
        "options": options or {},
        "status": "queued",
        "output_dir": str(JOBS / (job_id + "_out")),
        "jobfile": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_dir']).mkdir(parents=True, exist_ok=True)
    Path(job['jobfile']).write_text(json.dumps(job, indent=2))
    return job

def list_required_passes(job):
    # decide what passes needed based on options
    opts = job.get("options", {})
    passes = ["beauty"]
    if opts.get("need_shadow", True):
        passes += ["shadow"]
    if opts.get("need_z", False):
        passes += ["z"]
    if opts.get("need_motion", True):
        passes += ["motion"]
    return passes

def save_job(job):
    Path(job['jobfile']).write_text(json.dumps(job, indent=2))
    return job['jobfile']
