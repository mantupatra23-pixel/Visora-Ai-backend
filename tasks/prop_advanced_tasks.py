# tasks/prop_advanced_tasks.py
from celery import Celery
import os, subprocess, shlex, json
from pathlib import Path
from services.mesh_analyzer import save_handle_json
from services.physics_planner import plan_throw, save_plan

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('prop_adv', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_prop_advanced(self, jobfile):
    job = json.loads(Path(jobfile).read_text())
    outdir = Path("jobs/props") / (job['job_id'] + "_adv_out")
    outdir.mkdir(parents=True, exist_ok=True)
    # 1) compute handle via mesh_analyzer (if enabled)
    mesh_path = job.get('prop_path')
    handle_json = None
    if job.get('auto_fit', True) and mesh_path:
        handle_json = save_handle_json(mesh_path)
    # 2) call blender auto grip fit if handle found
    if handle_json:
        cmd = f"{BLENDER_BIN} --background --python blender_scripts/auto_grip_fit.py -- {shlex.quote(str(jobfile))} {shlex.quote(str(handle_json))} {shlex.quote(str(outdir))}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1200)
        if r.returncode != 0:
            return {"ok": False, "error": "auto_fit_failed", "stdout": r.stdout, "stderr": r.stderr}
    else:
        # fallback to grip_applier with chosen grip
        if job.get('grip_path'):
            cmd = f"{BLENDER_BIN} --background --python blender_scripts/grip_applier.py -- {shlex.quote(str(jobfile))} {shlex.quote(str(outdir))}"
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1200)
            if r.returncode != 0:
                return {"ok": False, "error": "grip_apply_failed", "stdout": r.stdout, "stderr": r.stderr}
    # 3) physics plan if requested (throw)
    if job.get('plan') and job['plan'].get('type')=='throw':
        start = job['plan'].get('from', [0,0,1])
        target = job['plan'].get('to', [3,0,1])
        plan = plan_throw(start, target, speed=job['plan'].get('speed',6.0))
        planfile = save_plan(job['job_id'], plan)
        cmd2 = f"{BLENDER_BIN} --background --python blender_scripts/throw_planner.py -- {shlex.quote(str(jobfile))} {shlex.quote(str(planfile))} {shlex.quote(str(outdir))}"
        r2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, timeout=1200)
        if r2.returncode != 0:
            return {"ok": False, "error": "throw_planner_failed", "stdout": r2.stdout, "stderr": r2.stderr}
    # done
    return {"ok": True, "outdir": str(outdir)}
