# routes/universe.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.universe_engine import UniverseEngine
from pathlib import Path

router = APIRouter()
ue = UniverseEngine()

class UniverseReq(BaseModel):
    script_text: str
    preferred_preset: str | None = None
    prefer_upload: bool | None = False
    user_image_path: str | None = None  # if prefer_upload true and user uploaded
    extra_prompt: str | None = None
    make_3d: bool | None = True
    want_video: bool | None = True
    voice_filename: str | None = None
    image_filename: str | None = None
    video_filename: str | None = None

@router.post("/create")
def create_universe(req: UniverseReq):
    try:
        if req.prefer_upload and req.user_image_path:
            if not Path(req.user_image_path).exists():
                raise HTTPException(status_code=404, detail="User image not found")

        out = ue.create_universe_asset(
            script_text=req.script_text,
            preferred_preset=req.preferred_preset,
            prefer_upload=bool(req.prefer_upload),
            user_image_path=req.user_image_path,
            extra_prompt=req.extra_prompt,
            make_3d=bool(req.make_3d),
            want_video=bool(req.want_video),
            voice_filename=req.voice_filename,
            image_filename=req.image_filename,
            video_filename=req.video_filename
        )
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
