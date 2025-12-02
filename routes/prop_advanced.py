# routes/prop_advanced.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.prop_engine import build_prop_job
from tasks.prop_advanced_tasks import run_prop_advanced
import json, os, uuid

router = APIRouter()

class PropAdvReq(BaseModel):
    script_line: str
    character: str = "charA"
    grip_name: str | None = None    # optional: choose grip from library
    auto_fit: bool = True
    plan: dict | None = None        # e.g., {"type":"throw","from":[0,0,1],"to":[4,0,1],"speed":6}
    name: str | None = None

@router.post("/prop/submit_advanced")
def submit_adv(req: PropAdvReq):
    job = build_prop_job(req.script_line, character=req.character, name=req.name)
    job['auto_fit'] = req.auto_fit
    job['plan'] = req.plan or {}
    # attach grip path if provided
    if req.grip_name:
        from services.grip_poses import load_grip
        grip = load_grip(req.grip_name)
        job['grip_name'] = req.grip_name
        job['grip_path'] = str((Path("assets") / "grips" / (req.grip_name + ".json")).resolve())
    # enqueue advanced task
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    task = run_prop_advanced.delay(job['output_path'])
    return {"ok": True, "job": job, "task_id": task.id}
