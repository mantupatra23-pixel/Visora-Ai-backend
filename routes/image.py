# routes/image.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.image_engine import ImageService

router = APIRouter()
img_service = ImageService()

class ImgReq(BaseModel):
    prompt: str
    filename: str | None = None
    width: int | None = 512
    height: int | None = 512
    steps: int | None = 20
    guidance: float | None = 7.5

@router.post("/generate")
def generate(req: ImgReq):
    try:
        out = img_service.generate(
            prompt=req.prompt,
            out_filename=req.filename,
            num_inference_steps=req.steps or 20,
            guidance_scale=req.guidance or 7.5,
            height=req.height or 512,
            width=req.width or 512
        )
        return {"ok": True, "image": out}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
