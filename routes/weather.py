# routes/weather.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from services.weather_engine import build_job, load_presets, get_status
from tasks.weather_tasks import run_weather_job
import json

router = APIRouter()

class WeatherReq(BaseModel):
    preset: str | None = None
    custom: dict | None = None
    scene_file: str | None = None
    frames: int = 240
    export: str = "frames"  # frames | blend | exr

@router.post("/weather/submit")
def submit(req: WeatherReq = Body(...)):
    job = build_job(req.preset, req.custom, req.scene_file, frames=req.frames, export=req.export)
    task = run_weather_job.delay(job['output_path'])
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/weather/presets")
def presets():
    return load_presets()

@router.get("/weather/status/{job_id}")
def status(job_id: str):
    s = get_status(job_id)
    if not s.get("job_id"):
        raise HTTPException(status_code=404, detail=s)
    return s
