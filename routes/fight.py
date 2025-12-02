# routes/fight.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tasks.fight_tasks import full_pipeline, plan_fight, run_baker
from pathlib import Path
import json

router = APIRouter()

class FightReq(BaseModel):
    script: str
    length_sec: int = 6
    fps: int = 24

@router.post("/fight/submit")
def submit(req: FightReq):
    task = full_pipeline.delay(req.script, req.length_sec, req.fps)
    return {"ok": True, "task_id": task.id}

@router.post("/fight/plan")
def plan(req: FightReq):
    jobfile = plan_fight.run(req.script, req.length_sec, req.fps)
    return {"ok": True, "jobfile": jobfile}
