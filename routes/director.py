# routes/director.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.auto_director import create_director_job
from pathlib import Path

router = APIRouter()

class Beat(BaseModel):
    t: float
    speaker: str | None = None
    action: str | None = None
    emphasis: float | None = 0.0

class Timeline(BaseModel):
    duration: float
    beats: list[Beat] | None = None
    segments: list | None = None

class DirectorReq(BaseModel):
    scene_blend: str
    timeline: Timeline
    preset: str | None = "cinematic"
    out_prefix: str | None = None

@router.post("/create")
def create(req: DirectorReq):
    if not Path(req.scene_blend).exists():
        raise HTTPException(status_code=404, detail="scene_blend not found")
    res = create_director_job(req.scene_blend, req.timeline.dict(), req.preset or "cinematic", req.out_prefix)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
