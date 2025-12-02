# routes/horror.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.horror_mood import detect_tension_level, emotion_tags
from services.horror_shots import compose_shots
from services.horror_audio import pick_audio
from tasks.horror_tasks import run_horror_job
from pathlib import Path
import json

router = APIRouter()

class HorrorReq(BaseModel):
    script: str
    fps: int = 24

@router.post("/horror/create")
def create_scene(req: HorrorReq):
    level = detect_tension_level(req.script)
    tags = emotion_tags(req.script)
    comp = compose_shots(level)
    job_id = f"horror_{level}_{abs(hash(req.script))%10000}"
    jobfile = Path("jobs/horror") / f"{job_id}.json"
    jobfile.parent.mkdir(parents=True, exist_ok=True)
    job = {"job_id": job_id, "level": level, "tags": tags, "timeline": comp["timeline"], "total_frames": comp["total_frames"], "audio": pick_audio(level)}
    jobfile.write_text(json.dumps(job, indent=2))
    task = run_horror_job.delay(str(jobfile))
    return {"ok": True, "task_id": task.id, "jobfile": str(jobfile)}
