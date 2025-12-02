# routes/mocap_pro.py  (extend)
from fastapi import APIRouter
from pydantic import BaseModel
from services.mocap_advanced import build_advanced_job
from tasks.mocap_advanced_tasks import run_mocap_advanced

router = APIRouter()

class AdvancedReq(BaseModel):
    script: str
    rig: str = "humanoid_mixamo"
    name: str | None = None
    options: dict | None = {}

@router.post("/mocap/submit_advanced")
def submit_advanced(req: AdvancedReq):
    """
    Build an advanced mocap job from the provided script and enqueue a Celery task to process it.

    Request JSON example:
    {
      "script": "...",            # mocap script or short DSL describing actions
      "rig": "humanoid_mixamo",   # optional rig template to use
      "name": "walk_run_mix",     # optional job name
      "options": { ... }          # optional extra options
    }
    """
    # build job manifest + write job file (build_advanced_job should return dict with 'output_path' etc)
    job = build_advanced_job(req.script, rig=req.rig, name=req.name, options=req.options or {})
    # enqueue celery task - pass job manifest path (or whatever build_advanced_job returns)
    task = run_mocap_advanced.delay(job['output_path'])
    return {"ok": True, "job": job, "task_id": task.id}
