# routes/storyboard.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.storyboard_renderer import render_thumbnail_moviepy, render_batch_thumbnails

router = APIRouter()

class ThumbSpec(BaseModel):
    width: int = 640
    height: int = 360
    background: str | None = None
    characters: list | None = []
    text: str | None = None

@router.post("/render")
def render(spec: ThumbSpec):
    res = render_thumbnail_moviepy(spec.dict())
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
