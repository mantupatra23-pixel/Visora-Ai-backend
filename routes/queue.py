# routes/queue.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from celery_app import celery
from pathlib import Path
import os
from typing import Any, Dict

router = APIRouter()

class JobReq(BaseModel):
    task: str  # "create_multichar_scene" or "render_with_blender"
    payload: Dict[str, Any] = {}

@router.post("/submit")
def submit_job(req: JobReq):
    try:
        if req.task == "create_multichar_scene":
            task = celery.send_task("create_multichar_scene", args=[req.payload], kwargs={})
        elif req.task == "render_with_blender":
            task = celery.send_task("render_with_blender", args=[req.payload], kwargs={})
        else:
            raise HTTPException(status_code=400, detail="Unknown task")
        return {"ok": True, "task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
def task_status(task_id: str):
    try:
        ar = AsyncResult(task_id, app=celery)
        res = {
            "task_id": task_id,
            "state": ar.state,
            "info": ar.info  # may be None or result/exception
        }
        # if job saved result json, return path
        result_file = Path("static/queue_results") / f"{task_id}.json"
        if result_file.exists():
            res["result_file"] = str(result_file)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revoke/{task_id}")
def revoke_task(task_id: str, terminate: bool = True, signal: str = "SIGTERM"):
    try:
        celery.control.revoke(task_id, terminate=terminate, signal=signal)
        return {"ok": True, "revoked": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
