# services/farm_manager.py
"""
Render Farm Manager core helpers.
- create_job(job_spec) -> writes job file, returns job_id
- split_frames(job_spec) -> returns list of frame tasks
- get_job_status(job_id) -> metadata from jobs dir
- simple persistence via JSON files under jobs/farm/
"""
import os, json, uuid, time
from pathlib import Path

ROOT = Path(".").resolve()
JOBS_DIR = ROOT / "jobs" / "farm"
TASKS_DIR = JOBS_DIR / "tasks"
RESULTS_DIR = JOBS_DIR / "results"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:10]

def create_job(job_spec: dict):
    """
    job_spec example:
    {
      "type":"composite" | "render" | "s2m" | "v2a",
      "job_name": "myshot_001",
      "start_frame": 1,
      "end_frame": 120,
      "priority": 5,
      "payload": {... engine specific ...},
      "max_retries": 2
    }
    """
    jid = job_spec.get("job_id") or f"job_{_tid()}"
    job_spec["job_id"] = jid
    job_spec["created_at"] = time.time()
    job_spec["status"] = "pending"
    jobfile = JOBS_DIR / f"{jid}.json"
    jobfile.write_text(json.dumps(job_spec, indent=2))
    # split into frame-level tasks for per-frame engines (if needed)
    tasks = split_frames(job_spec)
    for t in tasks:
        tfile = TASKS_DIR / f"{t['task_id']}.json"
        tfile.write_text(json.dumps(t, indent=2))
    return {"ok": True, "job_id": jid, "task_count": len(tasks)}

def split_frames(job_spec: dict):
    tasks = []
    st = int(job_spec.get("start_frame", job_spec.get("payload",{}).get("start_frame",1)))
    ed = int(job_spec.get("end_frame", st))
    # if single-frame job, create single task
    if ed < st:
        ed = st
    for f in range(st, ed+1):
        tid = f"task_{_tid()}"
        t = {
            "task_id": tid,
            "job_id": job_spec["job_id"],
            "frame": f,
            "status": "queued",
            "attempts": 0,
            "payload": {
                "type": job_spec.get("type"),
                "engine_payload": job_spec.get("payload", {}),
                "frame": f
            },
            "priority": job_spec.get("priority", 5),
            "created_at": time.time()
        }
        tasks.append(t)
    return tasks

def get_job_status(job_id: str):
    jf = JOBS_DIR / f"{job_id}.json"
    if not jf.exists():
        return {"ok": False, "error": "job_not_found"}
    job = json.loads(jf.read_text())
    # compute stats from task files
    tasks = list(TASKS_DIR.glob(f"*"))
    total = 0; done=0; failed=0; running=0; queued=0
    for tfile in tasks:
        t = json.loads(tfile.read_text())
        if t.get("job_id")!=job_id: continue
        total += 1
        st = t.get("status")
        if st=="done": done += 1
        elif st=="failed": failed += 1
        elif st=="running": running += 1
        elif st=="queued": queued += 1
    job["stats"] = {"total": total, "done": done, "failed": failed, "running": running, "queued": queued}
    return {"ok": True, "job": job}

def mark_task_status(task_id: str, status: str, res_payload: dict | None = None):
    tfile = TASKS_DIR / f"{task_id}.json"
    if not tfile.exists():
        return {"ok": False, "error": "task_not_found"}
    t = json.loads(tfile.read_text())
    t["status"] = status
    if "attempts" not in t: t["attempts"]=0
    if status in ("done","failed"):
        t["finished_at"] = time.time()
    tfile.write_text(json.dumps(t, indent=2))
    # write result artifact if provided
    if res_payload:
        (RESULTS_DIR / f"{task_id}.result.json").write_text(json.dumps(res_payload, indent=2))
    return {"ok": True}
