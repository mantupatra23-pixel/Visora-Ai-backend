# services/weather_engine.py
import json, time, uuid
from pathlib import Path

ROOT = Path(".").resolve()
JOBS_DIR = ROOT / "jobs" / "weather"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PRESET_FILE = ROOT / "assets" / "weather_presets.json"

def _tid(): return uuid.uuid4().hex[:8]

def load_presets():
    if PRESET_FILE.exists():
        return json.loads(PRESET_FILE.read_text())
    # fallback defaults
    return {
        "rain_light": {"type":"rain","intensity":0.4,"wind":4,"duration_sec":6,"wetness":0.3,"particle_size":0.02},
        "rain_heavy": {"type":"rain","intensity":0.95,"wind":12,"duration_sec":8,"wetness":0.9,"particle_size":0.03},
        "snow": {"type":"snow","intensity":0.6,"wind":2,"duration_sec":10,"particle_size":0.06},
        "fog_morning": {"type":"fog","density":0.08,"height":5,"color":[0.9,0.95,1.0]},
        "storm": {"type":"storm","intensity":1.0,"wind":20,"lightning":True,"duration_sec":12}
    }

def build_job(preset_name: str | None = None, custom: dict | None = None, scene_file: str | None = None, frames: int = 240, export: str = "frames"):
    presets = load_presets()
    base = presets.get(preset_name, {}) if preset_name else {}
    cfg = {**base, **(custom or {})}
    job_id = f"weather_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "preset": preset_name,
        "config": cfg,
        "scene_file": scene_file,
        "frames": frames,
        "export": export,   # "frames" or "blend" or "exr"
        "output_path": str(JOBS_DIR / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job

def save_job(job: dict):
    p = Path(job.get("output_path"))
    p.write_text(json.dumps(job, indent=2))
    return str(p)

def get_status(job_id: str):
    j = JOBS_DIR / f"{job_id}.json"
    if not j.exists(): return {"ok": False, "error": "not_found"}
    return json.loads(j.read_text())
