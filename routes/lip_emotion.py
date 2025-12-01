# routes/lip_emotion.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from services.lip_emotion import save_upload, create_lip_emotion_job, OUT
from pydantic import BaseModel
from pathlib import Path

router = APIRouter()

class LipReq(BaseModel):
    image_path: str | None = None
    audio_path: str | None = None
    text: str | None = None
    emotion: str | None = "neutral"
    engine: str | None = "sadtalker"
    out_name: str | None = None

@router.post("/submit")
async def submit(req: LipReq):
    if not req.image_path or not Path(req.image_path).exists():
        raise HTTPException(status_code=400, detail="image_path missing or not found")
    if not req.audio_path and not req.text:
        raise HTTPException(status_code=400, detail="provide audio_path or text")
    res = create_lip_emotion_job(req.image_path, audio_path=req.audio_path, text=req.text, emotion=req.emotion, engine=req.engine, out_name=req.out_name)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.post("/upload_face")
async def upload_face(file: UploadFile = File(...)):
    content = await file.read()
    path = save_upload(content, filename=file.filename)
    return {"ok": True, "path": path}

@router.get("/download/{fname}")
def download(fname: str):
    p = OUT / fname
    if not p.exists():
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True, "path": str(p)}
