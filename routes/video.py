# routes/video.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.video_engine import VideoService

router = APIRouter()
video_svc = VideoService()

class VideoReq(BaseModel):
    image: Optional[str] = None         # local path or prompt
    audio_file: Optional[str] = None    # local path to mp3/wav
    audio_text: Optional[str] = None    # text to be TTS'd (if audio_file omitted)
    output_name: Optional[str] = None
    vertical: Optional[bool] = False
    lipsync: Optional[bool] = False
    wav2lip_repo: Optional[str] = None
    add_subtitles: Optional[bool] = False

@router.post("/make")
def make_video(req: VideoReq):
    try:
        out = video_svc.orchestrate(
            image_or_prompt=req.image,
            audio_text=req.audio_text,
            audio_file=req.audio_file,
            output_name=req.output_name,
            vertical=req.vertical,
            use_lipsync=req.lipsync,
            wav2lip_repo=req.wav2lip_repo,
            add_subtitles=req.add_subtitles
        )
        return {"ok": True, "video": out}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}")
