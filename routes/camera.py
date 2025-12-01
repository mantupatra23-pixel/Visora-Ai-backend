# routes/camera.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.camera_director import CameraDirector
from typing import List, Dict

router = APIRouter()
director = CameraDirector()

class CameraReq(BaseModel):
    script_text: str
    characters: List[Dict] | None = None
    mood: str | None = None
    start_time: float | None = 0.0

@router.post("/plan")
def plan_camera(req: CameraReq):
    try:
        out = director.generate_choreography(req.script_text, req.characters, req.mood, req.start_time or 0.0)
        return {"ok": True, "plan": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
