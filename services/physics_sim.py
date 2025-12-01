# services/physics_sim.py
"""
Physics Simulation Engine wrapper
- Accepts job JSON (scene_blend optional), simulation type, targets, frames, and parameters
- Writes job file -> calls Blender headless script to run simulation and export caches or rendered frames
- Returns task id and expected output paths
Note: heavy work must run on worker machines with Blender installed.
"""
import os, json, uuid
from pathlib import Path
import subprocess, shlex

ROOT = Path(".").resolve()
JOBDIR = ROOT / "jobs" / "physics"
OUTDIR = ROOT / "static" / "physics"
JOBDIR.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

BLENDER_SCRIPT = str(ROOT / "blender_scripts" / "physics_worker.py")  # ensure exists

def _task_id():
    return uuid.uuid4().hex[:10]

def submit_physics_job(job_spec: dict):
    """
    job_spec example:
    {
      "scene_blend": "scenes/my_scene.blend",   # optional; if absent worker should use default template
      "sim_type": "rigid|cloth|softbody|fluid|smoke|destruction",
      "targets": [{"object":"Crate.001","type":"rigid","mass":5}, ...],
      "frames": [1,250],
      "bake_samples": 64,
      "export": {"type":"abc|fbx|exr","out_prefix":"static/physics/jobid_"},
      "gpu": True|False,
      "notes": "optional"
    }
    """
    tid = _task_id()
    job_spec["task_id"] = tid
    job_file = JOBDIR / f"physics_{tid}.json"
    with open(job_file, "w") as f:
        json.dump(job_spec, f, indent=2)
    # build blender command
    out_prefix = job_spec.get("export", {}).get("out_prefix") or str(OUTDIR / f"job_{tid}_")
    # call blender headless (non-blocking recommended; here we run as subprocess and return)
    cmd = f"blender --background {shlex.quote(job_spec.get('scene_blend',''))} --python {shlex.quote(BLENDER_SCRIPT)} -- {shlex.quote(str(job_file))} {shlex.quote(out_prefix)}"
    try:
        # spawn detached process so API returns immediately (or you can use Celery in production)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "task_id": tid, "job_file": str(job_file), "out_prefix": out_prefix}
