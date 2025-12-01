# routes/subtitle.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.subtitle_engine import generate_srt_from_lines, burn_in_subtitles
from pathlib import Path

router = APIRouter()

class Line(BaseModel):
    index: int
    text: str
    start: float
    end: float

class SRTReq(BaseModel):
    lines: list[Line]
    out_path: str | None = None

class BurnReq(BaseModel):
    video_path: str
    subtitle_path: str
    out_path: str | None = None
    font: str | None = "DejaVuSans.ttf"
    fontsize: int | None = 48
    color: str | None = "white"

@router.post("/generate_srt")
def generate_srt(req: SRTReq):
    try:
        lines = [l.dict() for l in req.lines]
        p = generate_srt_from_lines(lines, out_path=req.out_path)
        return {"ok": True, "srt": p}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/burn_in")
def burn(req: BurnReq):
    try:
        # basic validation
        if not Path(req.video_path).exists():
            raise HTTPException(status_code=404, detail="video not found")
        if not Path(req.subtitle_path).exists():
            raise HTTPException(status_code=404, detail="subtitle not found")
        outp = burn_in_subtitles(req.video_path, req.subtitle_path, out_path=req.out_path, font=req.font, fontsize=req.fontsize, color=req.color)
        return {"ok": True, "video": outp}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
