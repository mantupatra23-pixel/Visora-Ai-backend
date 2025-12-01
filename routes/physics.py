# routes/physics.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.physics_sim import submit_physics_job
from typing import List, Dict, Any
from pathlib import Path

router = APIRouter()

class TargetSpec(BaseModel):
    object: str
    type: str = "rigid"  # rigid|cloth|softbody|smoke|fluid|destruction
    mass: float | None = 1.0
    friction: float | None = 0.5
    restitution: float | None = 0.0
    active: bool | None = True
    quality: int | None = 5

class PhysicsJobReq(BaseModel):
    scene_blend: str | None = ""
    sim_type: str = "rigid"
    targets: List[TargetSpec] | None = []
    frames: List[int] | None = [1,250]
    export: Dict[str,Any] | None = {"type":"abc"}
    notes: str | None = ""

@router.post("/submit")
def submit_job(req: PhysicsJobReq):
    # basic check
    if req.scene_blend and not Path(req.scene_blend).exists():
        raise HTTPException(status_code=404, detail="scene_blend not found")
    job = req.dict()
    res = submit_physics_job(job)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
