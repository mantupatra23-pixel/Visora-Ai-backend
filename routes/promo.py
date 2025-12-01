# routes/promo.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.promo_generator import pick_best_clips
from tasks.promo_tasks import render_and_publish
from services.youtube_uploader import get_authorize_url, exchange_code_for_tokens
from pathlib import Path
import uuid, json

router = APIRouter()


# -----------------------------
# REQUEST MODEL
# -----------------------------
class PromoReq(BaseModel):
    master_video: str
    length: int = 15
    style: str = "short"
    ratio: str = "9:16"
    title: str | None = None
    script: str | None = None
    schedule_at: str | None = None      # ISO timestamp
    platform: list | None = ["youtube"] # ["youtube","x","tiktok"]
    auto_subtitles: bool = True
    lang: str | None = None
    tone: str = "energetic"
    ab_test: bool = False
    ab_platform: str = "local"
    ab_wait_seconds: int = 3600
# -----------------------------


# -----------------------------
# CREATE PROMO JOB
# -----------------------------
@router.post("/create")
def create_promo(req: PromoReq):
    if not Path(req.master_video).exists():
        raise HTTPException(status_code=404, detail="Master video not found")

    # create job record
    job_id = "promo_" + uuid.uuid4().hex[:8]
    job_dir = Path("jobs/promo")
    job_dir.mkdir(parents=True, exist_ok=True)

    jf = job_dir / f"{job_id}.json"
    job = req.dict()
    job.update({"job_id": job_id, "status": "queued"})

    jf.write_text(json.dumps(job, indent=2))

    # enqueue Celery task
    render_and_publish.delay(str(jf))

    return {"ok": True, "job_id": job_id}
# -----------------------------


# -----------------------------
# STATUS CHECK
# -----------------------------
@router.get("/status/{job_id}")
def status(job_id: str):
    jf = Path("jobs/promo") / f"{job_id}.json"
    if not jf.exists():
        raise HTTPException(status_code=404, detail="job not found")
    return json.loads(jf.read_text())
# -----------------------------


# -----------------------------
# YOUTUBE AUTH: GET AUTH URL
# -----------------------------
@router.get("/yt_auth_url")
def yt_auth():
    """
    Returns Google OAuth2 URL — open this link and allow YouTube upload permissions.
    """
    return {"url": get_authorize_url()}
# -----------------------------


# -----------------------------
# YOUTUBE AUTH: EXCHANGE CODE
# -----------------------------
@router.post("/yt_exchange")
def yt_exchange(payload: dict):
    """
    Post {"code": "<paste google auth code>"} to store refresh_token safely.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="missing code")

    res = exchange_code_for_tokens(code)
    return res
# -----------------------------
