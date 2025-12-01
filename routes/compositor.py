# routes/compositor.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.compositor import submit_comp_job, grade_with_ffmpeg
from typing import Dict, Any

router = APIRouter()

class CompJob(BaseModel):
    input_passes: Dict[str, str]
    start_frame: int = 1
    end_frame: int = 120
    denoise: Dict[str, Any] = {"method":"openimageio","strength":0.5}
    grade: Dict[str, Any] = {"type":"preset","name":"filmic"}
    output: Dict[str, Any] = {"type":"mp4","path":"static/compositor/out.mp4","fps":25}

@router.post("/submit")
def submit(job: CompJob):
    jobd = job.dict()
    res = submit_comp_job(jobd)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

class LUTReq(BaseModel):
    lut_path: str
    in_pattern: str
    out_video: str
    fps: int = 25
    codec: str = "libx264"
    crf: int = 18

@router.post("/grade_ffmpeg")
def ffgrade(req: LUTReq):
    res = grade_with_ffmpeg(req.lut_path, req.in_pattern, req.out_video, req.fps, req.codec, req.crf)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res
