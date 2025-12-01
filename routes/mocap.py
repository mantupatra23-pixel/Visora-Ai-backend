# routes/mocap.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from services.mocap import save_upload, run_mocap_pipeline, OUTDIR
from pathlib import Path
from pydantic import BaseModel
import shutil

router = APIRouter()

@router.post("/upload_video")
async def upload_video(file: UploadFile = File(...)):
    content = await file.read()
    if not file.filename.lower().endswith((".mp4",".mov",".avi",".mkv")):
        raise HTTPException(status_code=400, detail="video format not supported")
    saved = save_upload(content, filename=file.filename)
    return {"ok": True, "path": saved}

class MocapReq(BaseModel):
    video_path: str
    mode: str | None = "mediapipe"
    smooth_window: int | None = 5
    lift_method: str | None = "simple"
    out_name: str | None = None

@router.post("/start")
def start_mocap(req: MocapReq):
    # Basic sanity
    if not Path(req.video_path).exists():
        raise HTTPException(status_code=404, detail="video not found")
    res = run_mocap_pipeline(req.video_path, mode=req.mode or "mediapipe", smooth_w=req.smooth_window or 5, lift_method=req.lift_method or "simple", out_name=req.out_name)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.get("/download/{fname}")
def download_bvh(fname: str):
    p = Path(OUTDIR) / fname
    if not p.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return {"ok": True, "path": str(p)}
