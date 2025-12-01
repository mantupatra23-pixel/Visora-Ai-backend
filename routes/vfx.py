# routes/vfx.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.visual_vfx import apply_glow_ffmpeg, apply_color_grade, apply_motion_blur, composite_overlays, chroma_key_composite, apply_lens_flare, speed_ramp_segments
from pathlib import Path

router = APIRouter()

class GlowReq(BaseModel):
    video_in: str
    out: str | None = None
    intensity: float | None = 0.6
    radius: int | None = 15

@router.post("/glow")
def glow(req: GlowReq):
    if not Path(req.video_in).exists():
        raise HTTPException(status_code=404, detail="video not found")
    res = apply_glow_ffmpeg(req.video_in, out_path=req.out, intensity=req.intensity, radius=req.radius)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res)
    return res

class GradeReq(BaseModel):
    video_in: str
    out: str | None = None
    lut: str | None = None
    contrast: float | None = 1.0
    saturation: float | None = 1.0

@router.post("/grade")
def grade(req: GradeReq):
    if not Path(req.video_in).exists():
        raise HTTPException(status_code=404, detail="video not found")
    res = apply_color_grade(req.video_in, out_path=req.out, lut_path=req.lut, contrast=req.contrast, saturation=req.saturation)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res)
    return res

class MBReq(BaseModel):
    video_in: str
    out: str | None = None

@router.post("/mblur")
def mblur(req: MBReq):
    if not Path(req.video_in).exists():
        raise HTTPException(status_code=404, detail="video not found")
    res = apply_motion_blur(req.video_in, out_path=req.out)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res)
    return res

class CKReq(BaseModel):
    fg: str
    bg: str
    out: str | None = None
    key_color: str | None = "0x00FF00"
    similarity: float | None = 0.1
    blend: float | None = 0.1

@router.post("/chroma")
def chroma(req: CKReq):
    if not Path(req.fg).exists() or not Path(req.bg).exists():
        raise HTTPException(status_code=404, detail="file not found")
    res = chroma_key_composite(req.fg, req.bg, out_path=req.out, key_color=req.key_color, similarity=req.similarity, blend=req.blend)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res)
    return res
