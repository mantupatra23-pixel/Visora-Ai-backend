# services/scheduler.py
import time, os, json, random
from pathlib import Path
from datetime import datetime, timedelta
from tasks.farm_tasks import run_task
from services.node_monitor import list_nodes
from services.farm_manager import TASKS_DIR, mark_task_status if False else None

ROOT = Path(".").resolve()
TASKS_DIR = ROOT / "jobs" / "farm" / "tasks"

# scheduler config
POLL_INTERVAL = int(os.getenv("SCHED_POLL_SECS", "3"))
MAX_CONCURRENT = int(os.getenv("SCHED_MAX_CONCURRENT", "8"))
CLAIM_TTL = int(os.getenv("SCHED_CLAIM_TTL", "300"))  # sec

# small in-memory trackers (restart-safe tasks remain in tasks dir)
claimed = {}  # task_id -> claimed_at

def can_dispatch():
    # simple concurrency heuristic
    return len(claimed) < MAX_CONCURRENT

def claim_task(tpath: Path):
    try:
        t = json.loads(tpath.read_text())
        tid = t['task_id']
        if t.get('status') in ('running','done'): 
            return False
        # mark running
        t['status'] = 'queued_for_dispatch'
        t['claimed_at'] = time.time()
        tpath.write_text(json.dumps(t, indent=2))
        claimed[tid] = time.time()
        # dispatch through celery
        run_task.delay(str(tpath))
        # update status to running (worker will finalize)
        t['status'] = 'running'
        tpath.write_text(json.dumps(t, indent=2))
        print(f"Dispatched {tid}")
        return True
    except Exception as e:
        print("Claim failed", e)
        return False

def sweep_claims():
    # remove stale claims older than TTL (to allow re-dispatch)
    now = time.time()
    stale = [tid for tid,at in claimed.items() if now - at > CLAIM_TTL]
    for tid in stale:
        # find file and reset
        for f in TASKS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get('task_id') == tid and data.get('status') == 'running':
                    data['status'] = 'queued'
                    f.write_text(json.dumps(data, indent=2))
            except:
                pass
        claimed.pop(tid, None)

def pick_task():
    # prioritise lower attempts, higher priority tasks
    tasks = []
    for f in TASKS_DIR.glob("*.json"):
        try:
            t = json.loads(f.read_text())
            if t.get('status') in ("queued", "queued_for_dispatch"):
                t['_path'] = str(f)
                tasks.append(t)
        except:
            continue
    if not tasks: return None
    # sort by (attempts asc, priority desc, created_at asc)
    tasks.sort(key=lambda x: (x.get('attempts',0), -int(x.get('priority',5)), x.get('created_at',0)))
    return tasks[0]

def run_loop():
    print("Scheduler started at", datetime.utcnow().isoformat())
    while True:
        try:
            sweep_claims()
            if not can_dispatch():
                time.sleep(POLL_INTERVAL)
                continue
            t = pick_task()
            if not t:
                time.sleep(POLL_INTERVAL)
                continue
            p = Path(t['_path'])
            # final check and attempt to claim
            claimed_ok = claim_task(p)
            if not claimed_ok:
                time.sleep(0.2)
                continue
        except KeyboardInterrupt:
            print("Scheduler stopping")
            break
        except Exception as e:
            print("Scheduler error:", e)
            time.sleep(1)

if __name__ == "__main__":
    run_loop()
