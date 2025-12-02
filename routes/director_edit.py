# routes/director_edit.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.edit_rules import generate_edl_for_job
from services.lens_picker import pick_lens_for_shot
from tasks.director_tasks import run_director_job
from pathlib import Path
import json, subprocess, shlex
from tasks import director_tasks

router = APIRouter()

class EDLReq(BaseModel):
    job_id: str

@router.post("/director/export_edl")
def export_edl(req: EDLReq):
    jobfile = Path("jobs/director") / f"{req.job_id}.json"
    if not jobfile.exists(): raise HTTPException(status_code=404, detail="job not found")
    out = Path("jobs/director") / f"{req.job_id}.edl"
    path = generate_edl_for_job(str(jobfile), str(out))
    return {"ok": True, "edl_path": path}

class LensReq(BaseModel):
    desired_dof: str = "shallow"
    subject_distance_m: float = 2.0
    sensor: str = "full_frame"

@router.post("/director/pick_lens")
def pick_lens(req: LensReq):
    res = pick_lens_for_shot(req.desired_dof, req.subject_distance_m, req.sensor)
    return {"ok": True, "lens": res}
