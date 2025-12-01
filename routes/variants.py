# routes/variants.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_variant import generate_variants

router = APIRouter()

class VarReq(BaseModel):
    scene_plan: dict
    style: str = "cinematic"
    n: int = 3

@router.post("/variants")
def variants(req: VarReq):
    res = generate_variants(req.scene_plan, req.style, req.n)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
