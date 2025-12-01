# routes/dubbing.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.multichar_dubbing import generate_tracks

router = APIRouter()

class DubReq(BaseModel):
    script_lines: list
    voices: dict

@router.post("/generate")
def gen(req: DubReq):
    return generate_tracks(req.script_lines, req.voices)
