# routes/romantic.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.romantic_emotion import romantic_level
from services.romantic_shot import compose_romantic
from tasks.romantic_tasks import romantic_pipeline
from pathlib import Path
import json

router = APIRouter()

class RomanticReq(BaseModel):
    script: str
    fps: int = 24

@router.post("/romantic/create")
def romantic_scene(req: RomanticReq):
    level = romantic_level(req.script)
    shots = compose_romantic(level, req.fps)

    job_id = "rom_" + level
    jobfile = Path("jobs/romantic") / f"{job_id}.json"
    jobfile.parent.mkdir(parents=True, exist_ok=True)

    job = {
        "job_id": job_id,
        "level": level,
        "timeline": shots
    }
    jobfile.write_text(json.dumps(job, indent=2))

    task = romantic_pipeline.delay(str(jobfile))
    return {"ok":True, "task_id":task.id, "level":level}
