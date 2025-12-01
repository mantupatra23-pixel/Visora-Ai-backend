# routes/template.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.template_engine import TemplateEngine

router = APIRouter()
tpl_engine = TemplateEngine()

class TemplateReq(BaseModel):
    template_name: str
    title: str
    body: str
    image_path: Optional[str] = None   # local path or prompt (auto image svc not called here)
    audio_path: Optional[str] = None   # local speech audio path (preferred)
    music_path: Optional[str] = None
    output_name: Optional[str] = None
    vertical: Optional[bool] = True
    add_subtitles: Optional[bool] = True

@router.post("/render")
def render_template(req: TemplateReq):
    try:
        res = tpl_engine.render_template(
            template_name=req.template_name,
            title=req.title,
            body=req.body,
            image_path=req.image_path,
            audio_path=req.audio_path,
            music_path=req.music_path,
            output_name=req.output_name,
            vertical=req.vertical,
            add_subtitles=req.add_subtitles
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error","unknown"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
