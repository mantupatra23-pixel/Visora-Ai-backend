# routes/director.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

from services.director_service import create_director_job
from tasks.director_tasks import run_director_job

router = APIRouter()

class DirectorReq(BaseModel):
    script: str
    name: str | None = None
    fps: int = 24
    length_sec: int = 12
    options: dict | None = {}

@router.post("/director/submit")
def submit(req: DirectorReq):
    """
    Create a director job JSON under jobs/director and enqueue the celery task.
    Returns the job manifest and the celery task id.
    """
    job = create_director_job(
        req.script,
        name=req.name,
        fps=req.fps,
        length_sec=req.length_sec,
        options=req.options or {}
    )
    # enqueue celery task (expects job['output_path'] to be absolute or relative path to json)
    task = run_director_job.delay(job["output_path"])
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/director/status/{job_id}")
def status(job_id: str):
    """
    Read job manifest/result from jobs/director/<job_id>.json
    """
    p = Path("jobs/director") / f"{job_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="job not found")
    return json.loads(p.read_text())
