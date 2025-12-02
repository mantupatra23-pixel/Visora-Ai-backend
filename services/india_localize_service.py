# services/india_localize_service.py
import time, uuid, json
from pathlib import Path
from services.india_lang_pack import LANGS, resolve_lang, available_langs

JOBS = Path("jobs/india_localize")
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def create_localization_job(source_media: str, src_lang_hint: str | None, target_langs: list, options: dict | None = None):
    job_id = f"loc_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "source_media": source_media,
        "src_lang_hint": src_lang_hint,
        "target_langs": target_langs,
        "options": options or {},
        "status": "queued",
        "steps": [],
        "output_dir": str(JOBS / (job_id + "_out")),
        "jobfile": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_dir']).mkdir(parents=True, exist_ok=True)
    Path(job['jobfile']).write_text(json.dumps(job, indent=2))
    return job

def update_job(jobfile, updates: dict):
    p = Path(jobfile)
    job = json.loads(p.read_text())
    job.update(updates)
    p.write_text(json.dumps(job, indent=2))
    return job

def list_supported_languages():
    return available_langs()
