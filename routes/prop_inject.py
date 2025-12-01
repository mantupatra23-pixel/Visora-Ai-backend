# routes/prop_inject.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from pydantic import BaseModel
from services.prop_injector import list_available_props, register_prop, create_injection_job, PROPS_DIR
from pathlib import Path
import shutil

router = APIRouter()

class PropMeta(BaseModel):
    name: str
    model: str
    bbox: list | None = None
    hand_grip: dict | None = None
    physics: dict | None = None

@router.get("/list")
def list_props():
    return {"ok": True, "props": list_available_props()}

@router.post("/register")
async def upload_prop(file: UploadFile = File(...), meta: str | None = Body(None)):
    # upload model file into assets/props and optionally register meta JSON (meta is json string)
    filename = file.filename
    dest = PROPS_DIR / filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    # if meta provided, write json meta next to model
    if meta:
        try:
            import json
            m = json.loads(meta)
            if "model" not in m:
                m["model"] = filename
            register_prop(m)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "path": str(dest)}

class InjectAction(BaseModel):
    prop: str
    target: str | None = None
    attach: str | None = None       # e.g., "right_hand" or bone name
    position: list | None = None
    rotation: list | None = None
    scale: float | None = 1.0
    physics: bool | None = False

class JobReq(BaseModel):
    scene_blend: str
    actions: list[InjectAction]
    out_prefix: str | None = None

@router.post("/inject")
def inject(req: JobReq):
    # basic checks
    if not Path(req.scene_blend).exists():
        raise HTTPException(status_code=404, detail="scene_blend not found")
    acts = [a.dict() for a in req.actions]
    res = create_injection_job(req.scene_blend, acts, out_prefix=req.out_prefix)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
