# services/physics_job_manager.py
import json, os, time
from pathlib import Path

ROOT = Path(".").resolve()
JOBDB = ROOT / "jobs" / "physics_db.json"
JOBDB.parent.mkdir(parents=True, exist_ok=True)
if not JOBDB.exists():
    JOBDB.write_text(json.dumps({}, indent=2))

def _load():
    return json.loads(JOBDB.read_text())

def _save(data):
    JOBDB.write_text(json.dumps(data, indent=2))

def create_job_record(task_id, job_file, out_prefix, status="queued"):
    db = _load()
    db[task_id] = {"job_file": job_file, "out_prefix": out_prefix, "status": status, "logs": [], "created": time.time()}
    _save(db)
    return db[task_id]

def update_job_status(task_id, status, log=None):
    db = _load()
    if task_id not in db:
        return False
    db[task_id]["status"] = status
    if log:
        db[task_id]["logs"].append({"ts": time.time(), "log": log})
    _save(db)
    return True

def get_job(task_id):
    db = _load()
    return db.get(task_id)
