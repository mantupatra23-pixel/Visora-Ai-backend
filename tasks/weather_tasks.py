# tasks/weather_tasks.py  (updated)
from celery import Celery
import os, subprocess, shlex, json
from pathlib import Path
import time

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('weather', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_weather_job(self, jobfile_path: str):
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error": "jobfile_missing"}
    job = json.loads(jobf.read_text())
    out_dir = Path("jobs/weather") / (job['job_id'] + "_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    features = job.get("features", {})
    # Base baker always runs
    baker = Path("blender_scripts") / "weather_baker.py"
    cmd_base = f"{BLENDER_BIN} --background --python {shlex.quote(str(baker))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"
    try:
        proc = subprocess.run(cmd_base, shell=True, capture_output=True, text=True, timeout=7200)
        if proc.returncode != 0:
            res = {"ok": False, "step":"base_baker","stdout":proc.stdout,"stderr":proc.stderr,"rc":proc.returncode}
            (out_dir / "result.json").write_text(json.dumps(res, indent=2))
            return res
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error":"timeout_base","detail":str(e)}
    # run optional advanced modules
    results = {"base": True}
    # A) FLIP fluid splashes
    if features.get("flip_fluid"):
        flip_script = Path("blender_scripts") / "weather_flip_fluid.py"
        cmd = f"{BLENDER_BIN} --background --python {shlex.quote(str(flip_script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=14400)
            results['flip_fluid'] = (p.returncode == 0)
            results['flip_fluid_stdout'] = p.stdout[:4000]
            results['flip_fluid_stderr'] = p.stderr[:4000]
        except subprocess.TimeoutExpired as e:
            results['flip_fluid'] = False; results['flip_fluid_error']="timeout"
    # B) Lightning + audio sync
    if features.get("lightning_audio"):
        la_script = Path("blender_scripts") / "weather_lightning_audio.py"
        cmd = f"{BLENDER_BIN} --background --python {shlex.quote(str(la_script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
        results['lightning_audio'] = (p.returncode == 0)
        results['lightning_audio_stdout'] = p.stdout[:4000]
    # C) Puddles & reflections
    if features.get("puddles"):
        puddle_script = Path("blender_scripts") / "weather_puddles.py"
        p = subprocess.run(f"{BLENDER_BIN} --background --python {shlex.quote(str(puddle_script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}", shell=True, capture_output=True, text=True, timeout=3600)
        results['puddles'] = (p.returncode == 0)
        results['puddles_stdout'] = p.stdout[:4000]
        results['puddles_stderr'] = p.stderr[:4000]
    # D) Transition timeline
    if features.get("transition"):
        trans_script = Path("blender_scripts") / "weather_transition.py"
        p = subprocess.run(f"{BLENDER_BIN} --background --python {shlex.quote(str(trans_script))} -- {shlex.quote(str(jobf))} {shlex.quote(str(out_dir))}", shell=True, capture_output=True, text=True, timeout=3600)
        results['transition'] = (p.returncode == 0)
        results['transition_stdout'] = p.stdout[:4000]
        results['transition_stderr'] = p.stderr[:4000]
    # collect logs
    (out_dir / "result.json").write_text(json.dumps({"ok": True, "features": results}, indent=2))
    return {"ok": True, "features": results}
