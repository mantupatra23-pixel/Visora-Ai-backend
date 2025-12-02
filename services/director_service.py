# services/director_service.py
import json, time, uuid
from pathlib import Path
from services.camera_utils import build_shot_list
JOBS = Path("jobs/director")
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def create_director_job(script_text: str, name: str | None = None, fps:int =24, length_sec: int = 12, options: dict | None = None):
    job_id = name or f"dir_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "script": script_text,
        "fps": fps,
        "length_sec": length_sec,
        "options": options or {},
        "plan": build_shot_list(script_text, length_sec=length_sec, fps=fps),
        "output_path": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job
