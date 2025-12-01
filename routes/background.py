# routes/background.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.background_engine import BackgroundEngine
from pathlib import Path

router = APIRouter()
bg = BackgroundEngine()

class BGReq(BaseModel):
    preset_key: str | None = None
    script_text: str | None = None
    explicit_mood: str | None = None
    out_name: str | None = None

@router.post("/generate")
def generate_bg(req: BGReq):
    try:
        res = bg.generate_background(req.preset_key, req.script_text, req.explicit_mood, req.out_name)
        if not res.get("ok"):
            raise HTTPException(status_code=500, detail=res.get("error","Unknown"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
