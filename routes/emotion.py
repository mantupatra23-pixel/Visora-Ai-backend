# routes/emotion.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from services.emotion_classifier import classify_audio, classify_image

router = APIRouter()


class AudioReq(BaseModel):
    audio_path: str


class ImageReq(BaseModel):
    image_path: str


@router.post("/audio")
def audio(req: AudioReq) -> Dict[str, Any]:
    """
    Classify emotion from an audio file path.
    Returns JSON: {"ok": True, "result": <classifier result>}
    """
    try:
        res = classify_audio(req.audio_path)
        return {"ok": True, "result": res}
    except ValueError as e:
        # client error (e.g. file not found / invalid file)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # unexpected server error
        raise HTTPException(status_code=500, detail=f"Audio classification failed: {e}")


@router.post("/image")
def image(req: ImageReq) -> Dict[str, Any]:
    """
    Classify emotion from an image file path.
    Returns JSON: {"ok": True, "result": <classifier result>}
    """
    try:
        res = classify_image(req.image_path)
        return {"ok": True, "result": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image classification failed: {e}")
