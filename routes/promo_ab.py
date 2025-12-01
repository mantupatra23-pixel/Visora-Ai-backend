# routes/promo_ab.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tasks.promo_ab_tasks import run_ab_test
from pathlib import Path
import json

router = APIRouter()

class ABReq(BaseModel):
    jobfile: str
    platform: str = "local"

@router.post("/start")
def start(req: ABReq):
    jf = Path(req.jobfile)
    if not jf.exists(): raise HTTPException(status_code=404, detail="jobfile missing")
    task = run_ab_test.delay(str(jf), platform=req.platform)
    return {"ok": True, "task_id": task.id}
