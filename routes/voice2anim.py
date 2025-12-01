# routes/voice2anim.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.voice2anim import save_audio, run_voice2anim_pipeline, OUT
from pathlib import Path

router = APIRouter()

@router.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    content = await file.read()
    if not file.filename.lower().endswith((".wav",".mp3",".flac")):
        raise HTTPException(status_code=400, detail="audio format not supported")
    path = save_audio(content, filename=file.filename)
    return {"ok": True, "path": path}

class V2AReq(BaseModel):
    wav_path: str
    profile: dict | None = {}
    mode: str | None = "fast"   # "fast" or "hq"
    out_name: str | None = None

@router.post("/start")
def start(req: V2AReq):
    if not Path(req.wav_path).exists():
        raise HTTPException(status_code=404, detail="audio missing")
    res = run_voice2anim_pipeline(req.wav_path, profile=req.profile or {}, mode=req.mode or "fast", out_name=req.out_name)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.get("/download/{fname}")
def download(fname: str):
    p = OUT / fname
    if not p.exists():
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "path": str(p)}
