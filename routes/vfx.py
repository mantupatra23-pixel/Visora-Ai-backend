# routes/vfx.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.compositor_service import make_vfx_job, save_job
from tasks.vfx_tasks import run_planar_key_and_vfx, run_plate_replace
from pathlib import Path
import json

router = APIRouter()

class VFXReq(BaseModel):
    plate: str
    reference: str | None = None
    options: dict | None = {}

@router.post("/vfx/submit")
def submit(req: VFXReq):
    """
    Create a VFX job (planar tracking/keying + compositing).
    Returns job metadata and enqueues a celery task to run the VFX pipeline.
    """
    job = make_vfx_job(req.plate, req.reference, req.options)
    save_job(job)  # writes jobfile into jobs/vfx/...
    # job['jobfile'] should be absolute or repo-relative path to the job file
    task = run_planar_key_and_vfx.delay(job['jobfile'])
    return {"ok": True, "job": job, "task_id": task.id}

class PlateReplaceReq(BaseModel):
    plate_path: str
    bg_video: str
    src_pts: list  # list of 4 [x,y] in plate coordinate space
    dst_pts: list  # list of 4 [x,y] in background coordinate space
    out_video: str

@router.post("/vfx/plate_replace")
def plate_replace(req: PlateReplaceReq):
    """
    Enqueue a plate replacement task (homography / planar warp + blend).
    Arguments:
      - plate_path: path to the foreground plate to be placed
      - bg_video: background video path
      - src_pts / dst_pts: four source/destination points for homography
      - out_video: path where result should be saved
    """
    # normalize/validate inputs
    if not Path(req.plate_path).exists():
        raise HTTPException(status_code=404, detail="plate not found")
    if not Path(req.bg_video).exists():
        raise HTTPException(status_code=404, detail="background video not found")
    if not (isinstance(req.src_pts, list) and isinstance(req.dst_pts, list)):
        raise HTTPException(status_code=400, detail="src_pts and dst_pts must be lists")
    t = run_plate_replace.delay(req.plate_path, req.bg_video, req.dst_pts, req.src_pts, req.out_video)
    return {"ok": True, "task_id": t.id}

@router.get("/vfx/status/{job_id}")
def status(job_id: str):
    """
    Return the job JSON saved in jobs/vfx/<job_id>.json (if exists).
    """
    p = Path("jobs/vfx") / f"{job_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="job not found")
    try:
        return json.loads(p.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read job file: {e}")
