# routes/physics_jobs.py
from fastapi import APIRouter, HTTPException
from services.physics_job_manager import get_job
router = APIRouter()

@router.get("/status/{task_id}")
def status(task_id: str):
    j = get_job(task_id)
    if not j:
        raise HTTPException(404, "job not found")
    return {"ok": True, "job": j}
