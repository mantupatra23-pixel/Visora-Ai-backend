# routes/face_reenact.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from services.face_reenact import save_uploaded_file, run_wav2lip, run_sadtalker, run_firstorder, OUTDIR
from pathlib import Path
import shutil, os

router = APIRouter()

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    # basic ext check
    if not file.filename.lower().endswith((".png",".jpg",".jpeg",".mp4",".mov",".wav",".mp3")):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    saved = save_uploaded_file(content, filename=file.filename)
    return {"ok": True, "path": saved}

class Wav2LipReq(BaseModel):
    target: str   # path on server (image or video)
    audio: str    # path on server
    fps: int | None = 25
    out_name: str | None = None

@router.post("/wav2lip")
def wav2lip(req: Wav2LipReq):
    if not Path(req.target).exists() or not Path(req.audio).exists():
        raise HTTPException(status_code=404, detail="target or audio not found")
    res = run_wav2lip(req.target, req.audio, out_name=req.out_name, fps=req.fps or 25)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

class SadReq(BaseModel):
    target_image: str
    audio: str
    out_name: str | None = None

@router.post("/sadtalker")
def sadtalk(req: SadReq):
    if not Path(req.target_image).exists() or not Path(req.audio).exists():
        raise HTTPException(status_code=404, detail="files not found")
    res = run_sadtalker(req.target_image, req.audio, out_name=req.out_name)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

class FOFMReq(BaseModel):
    source_image: str
    driving_video: str
    out_name: str | None = None

@router.post("/firstorder")
def firstorder(req: FOFMReq):
    if not Path(req.source_image).exists() or not Path(req.driving_video).exists():
        raise HTTPException(status_code=404, detail="files not found")
    res = run_firstorder(req.source_image, req.driving_video, out_name=req.out_name)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.get("/list_outputs")
def list_out():
    outs = []
    for f in Path(OUTDIR).glob("*"):
        outs.append(str(f))
    return {"ok": True, "outputs": outs}
