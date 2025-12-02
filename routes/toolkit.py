# routes/toolkit.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.multi_cam_director import build_multi_cam_plan
from services.mocap_retargeter import make_retarget_plan
from pathlib import Path
import json, subprocess, shlex, os

router = APIRouter()

class MultiCamReq(BaseModel):
    choreo_jobfile: str

@router.post("/toolkit/multicam/plan")
def multicam_plan(req: MultiCamReq):
    path = build_multi_cam_plan(req.choreo_jobfile)
    return {"ok":True, "plan": path}
