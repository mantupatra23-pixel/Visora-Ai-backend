# routes/lipsync.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.lipsync_engine import LipSyncEngine
from pathlib import Path

router = APIRouter()
engine = LipSyncEngine()

class LipReq(BaseModel):
    image_path: str
    audio_path: str
    output_name: str | None = None

@router.post("/generate")
def lipsync(req: LipReq):
    try:
        if not Path(req.image_path).exists():
            raise HTTPException(status_code=404, detail="Image not found")

        if not Path(req.audio_path).exists():
            raise HTTPException(status_code=404, detail="Audio not found")

        vid = engine.lipsync(req.image_path, req.audio_path, req.output_name)
        return {"ok": True, "video": vid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
