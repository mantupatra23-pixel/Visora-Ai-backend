from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.falcon_tts_engine import TTSService
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()
tts_service = TTSService()

class TTSRequest(BaseModel):
    text: str
    filename: str | None = None  # optional filename

@router.post("/speak")
def speak(req: TTSRequest):
    try:
        out_name = req.filename or None
        out_path = tts_service.synthesize(req.text, out_filename=out_name)
        # return path info and a direct URL (relative)
        return {"ok": True, "file": out_path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}")

@router.get("/download/{file_name}")
def download(file_name: str):
    p = Path("static/outputs") / file_name
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(p), filename=file_name, media_type="application/octet-stream")
