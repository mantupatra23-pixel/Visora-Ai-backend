# routes/voiceclone.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.voice_clone import save_uploaded_sample, create_voice_clone_from_samples, synthesize_text_with_speaker, UPLOADS, VOICES
from pathlib import Path
import shutil

router = APIRouter()

class CreateCloneReq(BaseModel):
    sample_paths: List[str]   # relative paths on server or uploaded file names
    speaker_id: Optional[str] = None

@router.post("/upload_sample")
async def upload_sample(file: UploadFile = File(...)):
    # Save uploaded file bytes
    data = await file.read()
    # optionally verify format (wav/16k mono) — simple check on extension
    if not file.filename.lower().endswith((".wav", ".mp3", ".flac")):
        raise HTTPException(status_code=400, detail="Only wav/mp3/flac allowed")
    saved = save_uploaded_sample(data, filename=file.filename)
    return {"ok": True, "path": saved}

@router.post("/create_clone")
def create_clone(payload: CreateCloneReq):
    # Validate sample paths exist (they can be full paths or relative to UPLOADS)
    valid = []
    for sp in payload.sample_paths:
        p = Path(sp)
        if not p.exists():
            # try UPLOADS folder
            pu = UPLOADS / sp
            if pu.exists():
                valid.append(str(pu))
            else:
                raise HTTPException(status_code=404, detail=f"sample not found: {sp}")
        else:
            valid.append(str(p))
    res = create_voice_clone_from_samples(valid, speaker_id=payload.speaker_id)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

class SynthesizeReq(BaseModel):
    speaker_id: str
    text: str
    out_filename: Optional[str] = None

@router.post("/synthesize")
def synthesize(req: SynthesizeReq):
    res = synthesize_text_with_speaker(req.speaker_id, req.text, out_filename=req.out_filename)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.get("/list_clones")
def list_clones():
    out = []
    for d in VOICES.iterdir():
        if d.is_dir():
            meta = {}
            mfile = d / "meta.json"
            if mfile.exists():
                try:
                    meta = eval(mfile.read_text())
                except Exception:
                    meta = {}
            out.append({"speaker_id": d.name, "meta": meta})
    return {"ok": True, "clones": out}

@router.post("/delete_clone")
def delete_clone(speaker_id: str = Form(...)):
    d = VOICES / speaker_id
    if not d.exists():
        raise HTTPException(status_code=404, detail="not found")
    shutil.rmtree(d)
    return {"ok": True, "deleted": speaker_id}
