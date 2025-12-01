# routes/action_scene.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.action_scene_engine import ActionSceneEngine
from typing import List, Dict
from pathlib import Path

router = APIRouter()
engine = ActionSceneEngine()

class CharSpec(BaseModel):
    name: str | None = None
    model_path: str | None = None
    image: str | None = None
    rigged: bool | None = True
    entry_start: float | None = 0.0
    entry_duration: float | None = 1.0
    x: float | None = 0.0
    y: float | None = 0.0
    z: float | None = 0.0
    scale: float | None = 1.0

class PlanReq(BaseModel):
    script_text: str
    characters: List[CharSpec] | None = None
    background: str | None = None
    audio: str | None = None
    out_name: str | None = None
    prefer_blender: bool | None = True

@router.post("/plan")
def plan(req: PlanReq):
    try:
        chars = [c.dict() for c in (req.characters or [])]
        plan = engine.plan_action_sequence(req.script_text, characters=chars)
        # prepare job for chosen pipeline
        if req.prefer_blender:
            job = engine.prepare_blender_job(plan, chars, background=req.background, audio=req.audio, out_name=req.out_name)
        else:
            job = engine.prepare_fallback_job(plan, chars, background=req.background, audio=req.audio, out_name=req.out_name)
        return {"ok": True, "plan": plan, "job": job}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
