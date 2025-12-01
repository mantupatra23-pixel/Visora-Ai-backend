# routes/text.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.text_engine import generate_text

router = APIRouter()

class GenReq(BaseModel):
    prompt: str
    mode: Optional[str] = None  # "local" or "openai"
    max_length: Optional[int] = 256

@router.post("/generate")
def api_generate(req: GenReq):
    try:
        out = generate_text(req.prompt, mode=req.mode, max_length=req.max_length)
        return {"ok": True, "input": req.prompt, "output": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RewriteReq(BaseModel):
    text: str
    style: Optional[str] = None  # e.g., "short", "formal", "seo"

@router.post("/rewrite")
def api_rewrite(req: RewriteReq):
    style = req.style or "improve"
    prompt = f"Rewrite the following text in a {style} style, preserving meaning:\n\n{req.text}"
    try:
        out = generate_text(prompt)
        return {"ok": True, "output": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ShortReq(BaseModel):
    text: str
    length: Optional[str] = "short"  # short / very_short / bullet

@router.post("/shorten")
def api_shorten(req: ShortReq):
    length = req.length or "short"
    prompt = f"Summarize the following text in {length} form, keep it concise:\n\n{req.text}"
    try:
        out = generate_text(prompt)
        return {"ok": True, "output": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
