# routes/beat_ui.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pathlib import Path
import uuid, shutil, json, os
from services.beat_analyzer import analyze_beats

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/beat/ui", response_class=HTMLResponse)
def beat_ui():
    # Simple HTML + JS that loads audio and beat markers via API
    html = (Path("web/beat_ui.html").read_text() if Path("web/beat_ui.html").exists()
            else "<h3>Beat UI not installed. Add web/beat_ui.html in repo/web/</h3>")
    return HTMLResponse(html)

@router.post("/beat/upload")
async def beat_upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp3",".wav",".ogg",".m4a"]:
        raise HTTPException(400,"unsupported audio type")
    name = f"{uuid.uuid4().hex}{ext}"
    out = UPLOAD_DIR / name
    with out.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok":True, "path": str(out)}

@router.post("/beat/analyze")
def beat_analyze(payload: dict):
    # payload: {"path": "uploads/....wav"}
    path = payload.get("path")
    if not path or not Path(path).exists():
        raise HTTPException(400, "path_missing_or_not_exists")
    res = analyze_beats(path, use_librosa=True)
    return JSONResponse(res)
