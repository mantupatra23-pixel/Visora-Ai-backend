# services/weather_advanced.py
import json, time, uuid
from pathlib import Path
ROOT = Path(".").resolve()
JOBS = ROOT / "jobs" / "weather"
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def build_advanced_job(preset=None, custom=None, scene_file=None, frames=240, export="frames", features=None):
    """
    features: dict enabling advanced features, e.g.
      {"flip_fluid": True, "lightning_audio": True, "puddles": True, "transition": {"to":"storm","duration":60}}
    """
    job_id = f"weather_adv_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "preset": preset,
        "config": custom or {},
        "scene_file": scene_file,
        "frames": frames,
        "export": export,
        "features": features or {},
        "output_path": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job

def load_job(path):
    return json.loads(Path(path).read_text())
