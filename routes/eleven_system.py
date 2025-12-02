from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tasks.eleven_dub_pipeline import eleven_full_dub
from services.elevenlabs_service import eleven_tts
from services.eleven_voice_clone_engine import eleven_clone

router = APIRouter()

class TTSReq(BaseModel):
    text: str
    lang: str = "hi"
    voice_id: str | None = None

@router.post("/eleven/tts")
def tts_api(req: TTSReq):
    res = eleven_tts(req.text, req.voice_id)
    if not res["ok"]:
        raise HTTPException(500, res["error"])
    return res

class CloneReq(BaseModel):
    sample: str
    name: str | None = None
    consent: bool = False

@router.post("/eleven/clone")
def clone_api(req: CloneReq):
    res = eleven_clone(req.sample, req.name, req.consent)
    if not res["ok"]:
        raise HTTPException(500, res["error"])
    return res

class DubReq(BaseModel):
    video: str
    lang: str = "hi"
    voice_id: str | None = None

@router.post("/eleven/dub")
def dub_api(req: DubReq):
    res = eleven_full_dub.delay(req.video, req.lang, req.voice_id)
    return {"ok": True, "task_id": res.id}
