# routes/multichar.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.multichar_engine import MultiCharacterEngine
from pathlib import Path

router = APIRouter()
mce = MultiCharacterEngine()

class MCReq(BaseModel):
    script_text: str
    prefer_upload: bool | None = False
    # optional mapping of preset_key -> user image path (if user uploads)
    user_images: dict | None = None
    make_lipsync: bool | None = False
    bg_override: str | None = None
    out_name: str | None = None

@router.post("/create_scene")
def create_scene(req: MCReq):
    try:
        # validate user image paths if provided
        if req.user_images:
            for k,v in req.user_images.items():
                if not Path(v).exists():
                    raise HTTPException(status_code=404, detail=f"User image not found: {v}")
        out = mce.create_scene_video(
            script=req.script_text,
            prefer_upload=bool(req.prefer_upload),
            user_images=req.user_images,
            make_lipsync=bool(req.make_lipsync),
            bg_override=req.bg_override,
            out_name=req.out_name
        )
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
