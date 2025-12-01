# routes/multichar_anim.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.multichar_anim_engine import MultiCharAnimEngine
from pathlib import Path

router = APIRouter()
engine = MultiCharAnimEngine(blender_path=os.getenv("BLENDER_PATH","blender"))

class CharacterSpec(BaseModel):
    name: str
    model_path: str | None = None   # .glb/.obj path (preferred)
    image: str | None = None        # fallback image (for 2D fallback)
    rigged: bool | None = False
    entry_start: float | None = 0.0
    entry_duration: float | None = 1.0
    x: float | None = 0.0
    y: float | None = 0.0
    z: float | None = 0.0
    scale: float | None = 1.0

class CameraCut(BaseModel):
    start: float
    end: float
    type: str | None = "orbit"
    params: dict | None = None

class AnimJob(BaseModel):
    characters: list[CharacterSpec]
    camera_cuts: list[CameraCut] | None = None
    background: str | None = None
    audio: str | None = None      # optional combined audio path
    duration: float | None = 15.0
    fps: int | None = 24
    prefer_blender: bool | None = True
    output_name: str | None = None

@router.post("/animate")
def animate(job: AnimJob):
    try:
        j = job.dict()
        out = engine.animate(j, prefer_blender=bool(j.get("prefer_blender", True)), output_name=j.get("output_name"))
        return {"ok": True, "video": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
