# routes/personality.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.personality_engine import PersonalityEngine
from typing import Dict, Any, List

router = APIRouter()
engine = PersonalityEngine()

class PersonaModel(BaseModel):
    label: str
    tts: Dict[str, Any]
    emotion_bias: Dict[str, float] = {}
    gesture_intensity: float = 0.5
    camera_pref: Dict[str, Any] = {}
    animation_presets: List[str] = []
    vocab_style: Dict[str, Any] = {}

@router.get("/list")
def list_personas():
    try:
        return {"ok": True, "personas": engine.list_personas()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get/{name}")
def get_persona(name: str):
    p = engine.get_persona(name)
    if not p:
        raise HTTPException(status_code=404, detail="persona not found")
    return {"ok": True, "persona": p}

@router.post("/save")
def save_persona(p: PersonaModel):
    try:
        engine.save_persona(p.dict())
        return {"ok": True, "saved": p.label}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApplyReq(BaseModel):
    character: Dict[str, Any]
    persona: str

@router.post("/apply")
def apply_persona(req: ApplyReq):
    try:
        res = engine.apply_persona_to_character(req.character, req.persona)
        return {"ok": True, "character": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
