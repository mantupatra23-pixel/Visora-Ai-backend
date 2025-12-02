# routes/prop.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.prop_engine import build_prop_job
from tasks.prop_tasks import run_prop_job
from pathlib import Path
import json

router = APIRouter()

class PropReq(BaseModel):
    script_line: str
    character: str = "charA"
    hand_hint: str | None = None
    name: str | None = None

@router.post("/prop/submit")
def submit(req: PropReq):
    job = build_prop_job(req.script_line, character=req.character, hand_hint=req.hand_hint, name=req.name)
    if not job.get("prop"):
        raise HTTPException(status_code=400, detail=job)
    task = run_prop_job.delay(job['output_path'])
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/prop/status/{job_id}")
def status(job_id: str):
    jfile = Path("jobs/props") / f"{job_id}.json"
    if not jfile.exists():
        raise HTTPException(status_code=404, detail="job not found")
    return json.loads(jfile.read_text())
