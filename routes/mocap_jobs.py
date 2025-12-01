from fastapi import APIRouter, HTTPException
from tasks.mocap_tasks import run_openpose_task, run_vp3d_task
from pydantic import BaseModel
from pathlib import Path
router = APIRouter()

class JobReq(BaseModel):
    video_path: str

@router.post("/enqueue_openpose")
def enqueue_openpose(req: JobReq):
    if not Path(req.video_path).exists():
        raise HTTPException(404,"video missing")
    task = run_openpose_task.delay(req.video_path)
    return {"ok": True, "task_id": task.id}

@router.post("/enqueue_vp3d")
def enqueue_vp3d(req: JobReq):
    if not Path(req.video_path).exists():
        raise HTTPException(404,"video missing")
    # assume openpose json dir prepared earlier
    task = run_vp3d_task.delay(req.video_path)
    return {"ok": True, "task_id": task.id}
