# routes/scene_planner.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from services.scene_planner import analyze_scene
router = APIRouter()

class SceneReq(BaseModel):
    script_text: str
    env: Dict[str,Any] = {}
    characters: List[Dict[str,Any]] = []
    mood: str = "day"
    num_cameras: int = 3

@router.post("/plan")
def plan_scene(req: SceneReq):
    try:
        res = analyze_scene(req.script_text, env=req.env, characters=req.characters, mood=req.mood, num_cameras=req.num_cameras)
        if not res.get("ok"):
            raise HTTPException(status_code=500, detail=res)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
