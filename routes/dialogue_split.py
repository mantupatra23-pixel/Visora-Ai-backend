# routes/dialogue_split.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.dialogue_split_engine import DialogueSplitter

router = APIRouter()
ds = DialogueSplitter()

class DSReq(BaseModel):
    script_text: str

@router.post("/split")
def split_dialogue(req: DSReq):
    try:
        parts = ds.split_dialogue(req.script_text)
        return {"ok": True, "dialogue": parts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
