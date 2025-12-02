# routes/wav2lip.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.wav2lip_service import prepare_job
from tasks.wav2lip_tasks import wav2lip_job
from pathlib import Path
import json

router = APIRouter()

class Wav2LipReq(BaseModel):
    video: str        # server path to face video (or uploaded path)
    audio: str | None = None  # optional path to audio file
    use_gan: bool = False
    consent: bool = False

@router.post("/wav2lip/submit")
def submit(req: Wav2LipReq):
    try:
        job = prepare_job(req.video, req.audio, consent=req.consent, options={"use_gan": req.use_gan})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    jobfile = Path(job['out_dir']) / "job.json"
    task = wav2lip_job.delay(str(jobfile), use_gan=req.use_gan)
    return {"ok": True, "job": job, "task_id": task.id}

@router.get("/wav2lip/status/{jobid}")
def status(jobid: str):
    p = Path("jobs/wav2lip")
    matches = list(p.glob(f"*{jobid}*/job.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="job not found")
    job = json.loads(matches[0].read_text())
    return {"ok": True, "job": job}
