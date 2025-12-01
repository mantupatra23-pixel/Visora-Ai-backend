# routes/orchestrator.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.planner_orchestrator import make_package

router = APIRouter()

class PackReq(BaseModel):
    script_text: str
    characters: list | None = []
    env: dict | None = {}
    style: str = "cinematic"
    n_variants: int = 2

@router.post("/package")
def package(req: PackReq):
    res = make_package(req.script_text, req.characters, req.env, req.style, req.n_variants)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
