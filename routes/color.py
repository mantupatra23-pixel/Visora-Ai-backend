# routes/color.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.color_grading import build_job, load_presets, detect_mood_from_image
from tasks.color_tasks import run_grading
from pathlib import Path
import json

router = APIRouter()

class GradeReq(BaseModel):
    input_path: str   # file or frames folder (must be accessible by server)
    preset: str | None = None
    lut_path: str | None = None
    protect_skin: bool = True

@router.post("/grade/submit")
def submit(req: GradeReq):
    job = build_job(req.input_path, preset=req.preset, output_dir=None, protect_skin=req.protect_skin)
    if req.lut_path: job['lut_path'] = req.lut_path
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    task = run_grading.delay(job['output_path'])
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/grade/presets")
def presets():
    return load_presets()

@router.get("/grade/detect/{image_path}")
def detect(image_path: str):
    r = detect_mood_from_image(image_path)
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r)
    return r
