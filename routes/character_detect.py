# routes/character_detect.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.character_detect_engine import CharacterDetectEngine

router = APIRouter()
engine = CharacterDetectEngine()

class CDReq(BaseModel):
    script_text: str

@router.post("/detect")
def detect(req: CDReq):
    try:
        chars = engine.detect_characters(req.script_text)
        return {"ok": True, "characters": chars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
