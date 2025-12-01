# tasks/farm_tasks.py
from celery import Celery
import os, json, time, shlex, subprocess
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('farm', broker=BROKER, backend=BROKER)

ROOT = Path(".").resolve()
TASKS_DIR = ROOT / "jobs" / "farm" / "tasks"
RESULTS_DIR = ROOT / "jobs" / "farm" / "results"

# Example worker entry: worker polls task files and claims one (naive). But with Celery we implement worker task wrapper.
@app.task(bind=True)
def run_task(self, task_json_path):
    """
    task_json_path: path to task file (TASKS_DIR/<task_id>.json)
    Worker should call this as run_task.delay(str(task_path))
    """
    try:
        tfile = Path(task_json_path)
        if not tfile.exists():
            return {"ok": False, "error": "task_missing"}
        t = json.loads(tfile.read_text())
        task_id = t['task_id']
        # mark running
        t['status'] = 'running'
        t['attempts'] = t.get('attempts',0) + 1
        tfile.write_text(json.dumps(t, indent=2))
        payload = t['payload']
        # dispatch by type — sample: call engine scripts or routes
        typ = payload.get('type')
        frame = payload.get('frame')
        engine_payload = payload.get('engine_payload',{})
        # Simple mapping: if type == 'composite', call composite script for single-frame mode
        if typ == "composite" or typ=="render":
            # assume blender script supports FRAME env var or single-frame mode
            # Here we call a CLI specified in engine_payload['cmd'] or fallback to composite_passes_oidn.py
            cmd = engine_payload.get('cmd')
            if not cmd:
                blender_script = ROOT / "blender_scripts" / "composite_passes_oidn.py"
                jobfile = engine_payload.get('jobfile')  # job JSON for compositor
                cmd = f"blender --background --python {str(blender_script)} -- {jobfile} {engine_payload.get('outdir','static/compositor/frames')}"
            # set FRAME env and run
            env = os.environ.copy()
            env['FRAME'] = str(frame)
            p = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=1800)
            ok = p.returncode == 0
            result = {"ok": ok, "stdout": p.stdout[:2000], "stderr": p.stderr[:2000]}
        else:
            # unknown type fallback: mark success
            result = {"ok": True, "note": "no-op task type"}
        # write result
        (RESULTS_DIR / f"{task_id}.result.json").write_text(json.dumps(result, indent=2))
        t['status'] = 'done' if result.get('ok') else 'failed'
        t['finished_at'] = time.time()
        tfile.write_text(json.dumps(t, indent=2))
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}
