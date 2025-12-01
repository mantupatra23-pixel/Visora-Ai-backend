# routes/prop_tools.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.prop_lod import generate_lods
from services.prop_injector import register_prop
import json, os
router = APIRouter()

class LODReq(BaseModel):
    model_path: str
    prop_name: str
    lod_levels: list | None = [0.5,0.25,0.12]

@router.post("/gen_lods")
def gen_lods(req: LODReq):
    if not os.path.exists(req.model_path):
        raise HTTPException(404, "model not found")
    res = generate_lods(req.model_path, lod_levels=req.lod_levels)
    if not res.get("ok"):
        raise HTTPException(500, res)
    # auto-register meta referencing produced lods (simple)
    # find files in assets/props/lods matching base name
    # returning response only
    return res
