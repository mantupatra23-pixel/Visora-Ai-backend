# routes/presets.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.preset_engine import PresetEngine
from pathlib import Path

router = APIRouter()
pe = PresetEngine()

class ListResp(BaseModel):
    pass

class ApplyReq(BaseModel):
    preset_key: str
    input_image: str
    extra_prompt: str | None = None

@router.get("/list")
def list_presets():
    return {"ok": True, "presets": pe.list_presets()}

@router.post("/apply")
def apply_preset(req: ApplyReq):
    try:
        if not Path(req.input_image).exists():
            raise HTTPException(status_code=404, detail="Input image not found")
        res = pe.apply_preset_to_image(req.preset_key, req.input_image, extra_prompt_add=req.extra_prompt)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
