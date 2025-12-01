# routes/auto.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.auto_engine import AutoEngine

router = APIRouter()
auto = AutoEngine()

class AutoReq(BaseModel):
    prompt: str
    mode_text: Optional[str] = None

    want_image: Optional[bool] = True
    want_audio: Optional[bool] = True
    want_video: Optional[bool] = True

    voice_filename: Optional[str] = None
    image_filename: Optional[str] = None
    video_filename: Optional[str] = None

    vertical: Optional[bool] = True
    add_subtitles: Optional[bool] = True
    max_text_len: Optional[int] = 300

@router.post("/create")
def create(req: AutoReq):
    try:
        out = auto.create_pipeline(
            prompt=req.prompt,
            mode_text=req.mode_text,

            want_image=req.want_image,
            want_audio=req.want_audio,
            want_video=req.want_video,

            voice_filename=req.voice_filename,
            image_filename=req.image_filename,
            video_filename=req.video_filename,

            vertical=req.vertical,
            add_subtitles=req.add_subtitles,
            max_text_len=req.max_text_len
        )
        return out

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
