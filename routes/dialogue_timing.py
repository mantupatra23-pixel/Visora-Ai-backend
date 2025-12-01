# routes/dialogue_timing.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.dialogue_timing import DialogueTiming
from typing import List, Dict, Any

router = APIRouter()
engine = DialogueTiming(wpm=150)

class DTReq(BaseModel):
    script_text: str
    wpm: int | None = 150
    include_ssml: bool | None = True
    initial_offset: float | None = 0.0

@router.post("/analyze")
def analyze(req: DTReq):
    try:
        engine.wpm = int(req.wpm or 150)
        res = engine.analyze_script(req.script_text)
        lines = res["lines"]
        # make timeline with offsets
        timeline = engine.make_timeline(lines, initial_offset=float(req.initial_offset or 0.0))
        ssml = engine.emit_ssml_lines(timeline, include_wrapper=bool(req.include_ssml))
        return {"ok": True, "analysis": res, "timeline": timeline, "ssml": ssml}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
