# routes/soundfx.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.soundfx_engine import SoundFXEngine
from typing import List, Dict

router = APIRouter()
engine = SoundFXEngine()

class DialogueLine(BaseModel):
    audio: str
    start: float
    end: float
    speaker: str | None = None

class SFXReq(BaseModel):
    script_text: str
    dialogue_tracks: List[DialogueLine] | None = None
    mood: str | None = None
    music_intensity: str | None = None

@router.post("/mix")
def mix(req: SFXReq):
    try:
        dialogue_tracks = []
        if req.dialogue_tracks:
            for d in req.dialogue_tracks:
                dialogue_tracks.append(d.dict())
        out = engine.mix_tracks(dialogue_tracks, req.script_text, mood=req.mood, music_intensity=req.music_intensity)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
