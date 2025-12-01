# routes/multichar_enhanced.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.multichar_enhanced import MultiCharEnhancedEngine
from pathlib import Path
import os

router = APIRouter()
engine = MultiCharEnhancedEngine(voice_map=None)  # you can pass custom voice_map here

class EnhancedReq(BaseModel):
    script_text: str
    prefer_upload: bool | None = False
    user_images: dict | None = None
    make_lipsync: bool | None = True
    bg_override: str | None = None
    out_name: str | None = None

@router.post("/enhanced_create")
def enhanced_create(req: EnhancedReq):
    try:
        # validate user images if provided
        if req.user_images:
            for k,v in req.user_images.items():
                if not Path(v).exists():
                    raise HTTPException(status_code=404, detail=f"User image not found: {v}")
        out = engine.create_scene(
            script_text=req.script_text,
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
