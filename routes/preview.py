# routes/preview.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.preview_engine import PreviewEngine
from pathlib import Path

router = APIRouter()
pe = PreviewEngine()

class PreviewReq(BaseModel):
    script_text: str | None = None
    preset_key: str | None = None
    n: int | None = 3
    out_prefix: str | None = None

@router.post("/generate")
def generate_preview(req: PreviewReq):
    try:
        n = int(req.n) if req.n else 3
        if n < 1 or n > 6:
            raise HTTPException(status_code=400, detail="n must be 1..6")
        res = pe.generate_candidates(req.script_text, req.preset_key, n=n, out_prefix=req.out_prefix)
        return {"ok": True, "candidates": res}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
