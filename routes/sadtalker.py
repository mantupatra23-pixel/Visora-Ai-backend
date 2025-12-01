# routes/sadtalker.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.sadtalker_engine import SadTalkerEngine
from pathlib import Path

router = APIRouter()
# adjust repo_path/checkpoints if you cloned elsewhere
engine = SadTalkerEngine(repo_path="sadtalker_repo", checkpoints_dir="sadtalker_repo/checkpoints", python_bin="python")

class STReq(BaseModel):
    source_image: str          # local path e.g. static/outputs/person.png
    audio_path: str | None = None
    driving_video: str | None = None
    output_name: str | None = None
    extra_args: list | None = None

@router.post("/generate")
def generate(req: STReq):
    try:
        if not Path(req.source_image).exists():
            raise HTTPException(status_code=404, detail="Source image not found")
        if req.audio_path and not Path(req.audio_path).exists():
            raise HTTPException(status_code=404, detail="Audio not found")
        if req.driving_video and not Path(req.driving_video).exists():
            raise HTTPException(status_code=404, detail="Driving video not found")

        out = engine.generate(source_image=req.source_image, audio_path=req.audio_path, driver_video_or_npy=req.driving_video, output_name=req.output_name, extra_args=req.extra_args)
        return {"ok": True, "video": out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
