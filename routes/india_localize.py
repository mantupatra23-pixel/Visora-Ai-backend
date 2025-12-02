# routes/india_localize.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.india_localize_service import create_localization_job, list_supported_languages
from tasks.india_localization_tasks import full_localization_pipeline
from pathlib import Path
import json

router = APIRouter()

class LocalizeReq(BaseModel):
    source_media: str  # path to file on server
    src_lang_hint: str | None = None
    target_langs: list
    options: dict | None = {}

@router.post("/india/localize/submit")
def submit(req: LocalizeReq):
    # validate languages
    supported = list_supported_languages()
    for tl in req.target_langs:
        if tl not in supported and tl not in [k for k in supported]:
            # we allow codes defined in pack; if unknown, return error
            if tl not in supported:
                raise HTTPException(status_code=400, detail=f"target_lang_not_supported: {tl}")
    job = create_localization_job(req.source_media, req.src_lang_hint, req.target_langs, req.options)
    # start async pipeline
    task = full_localization_pipeline.delay(job['jobfile'])
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/india/localize/langs")
def langs():
    return {"ok": True, "languages": list_supported_languages()}
