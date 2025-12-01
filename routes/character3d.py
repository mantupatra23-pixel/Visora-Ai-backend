# routes/character3d.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.character3d_engine import Character3DEngine
from pathlib import Path

router = APIRouter()
engine = Character3DEngine()

class C3DReq(BaseModel):
    image_path: str

@router.post("/generate")
def generate_3d(req: C3DReq):
    try:
        if not Path(req.image_path).exists():
            raise HTTPException(status_code=404, detail="Image not found")

        mesh_path = engine.generate_character(req.image_path)
        return {"ok": True, "mesh": mesh_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
