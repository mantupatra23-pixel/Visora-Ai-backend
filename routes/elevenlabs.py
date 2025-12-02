# routes/elevenlabs.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.elevenlabs_service import tts_generate
from services.eleven_voice_clone import create_instant_clone, synthesize_clone_text

router = APIRouter()

class TTSReq(BaseModel):
    text: str
    voice_id: str | None = None
    out_name: str | None = None
    stability: float | None = None
    similarity_boost: float | None = None

@router.post("/eleven/tts")
def eleven_tts(req: TTSReq):
    res = tts_generate(req.text, voice_id=req.voice_id, output_name=req.out_name,
                       stability=req.stability, similarity_boost=req.similarity_boost)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return {"ok": True, "path": res["path"]}

class CloneReq(BaseModel):
    sample_path: str
    voice_name: str | None = None
    consent: bool = False

@router.post("/eleven/clone")
def eleven_clone(req: CloneReq):
    try:
        res = create_instant_clone(req.sample_path, voice_name=req.voice_name, consent=req.consent)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return {"ok": True, "voice_id": res["voice_id"], "resp": res.get("resp")}
