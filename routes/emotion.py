# routes/emotion.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.emotion_engine import EmotionEngine

router = APIRouter()
# set use_hf_model=True only if transformers & model installed
engine = EmotionEngine(use_hf_model=False)

class EmotionReq(BaseModel):
    text: str
    use_model: bool | None = False

@router.post("/detect")
def detect(req: EmotionReq):
    try:
        # optionally re-init engine with model (cheap)
        if req.use_model and not engine.use_hf:
            # you can reinitialize or return message; for now we return warning
            return {"ok": False, "msg": "HF model not enabled on this instance. Set use_hf_model=True in service init if you installed transformers & a model."}
        res = engine.analyze_and_map(req.text)
        return {"ok": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
