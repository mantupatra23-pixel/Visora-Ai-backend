# routes/dub.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tasks.dub_tasks import full_dubbing_pipeline
from pathlib import Path

router = APIRouter()

class DubReq(BaseModel):
    video_path: str
    lang_target: str = "hi"   # example: hindi
    voice_clone_id: str = None
    tts_engine: str = "coqui"
    consent: bool = False

@router.post("/dub/submit")
def dub_submit(req: DubReq):
    p = Path(req.video_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="video not found")
    task = full_dubbing_pipeline.delay(req.video_path, req.lang_target, req.voice_clone_id, req.tts_engine, req.consent)
    return {"ok": True, "task_id": task.id}
