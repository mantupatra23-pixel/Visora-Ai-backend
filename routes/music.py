# routes/music.py
from fastapi import APIRouter
from pydantic import BaseModel
from tasks.music_tasks import run_music_pipeline

router = APIRouter()

class MusicReq(BaseModel):
    audio_path: str
    anim_bank_dir: str
    dancers: list = ["DancerA","DancerB"]

@router.post("/music/run")
def run(req: MusicReq):
    task = run_music_pipeline.delay(req.audio_path, req.anim_bank_dir, req.dancers)
    return {"ok": True, "task_id": task.id}
