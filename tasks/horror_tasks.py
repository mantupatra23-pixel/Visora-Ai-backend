# tasks/horror_tasks.py
from celery import Celery
import shlex, subprocess, json
from pathlib import Path
import os

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
FFMPEG = os.getenv("FFMPEG","ffmpeg")
app = Celery('horror', broker=BROKER, backend=BROKER)

@app.task
def run_horror_job(jobfile):
    job = json.loads(Path(jobfile).read_text())
    out = Path("jobs/horror") / (Path(jobfile).stem + "_out")
    out.mkdir(parents=True, exist_ok=True)
    # 1) run Blender VFX
    script = Path("blender_scripts") / "horror_vfx.py"
    cmd = f"{BLENDER_BIN} --background --python {script} -- {jobfile} {out}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    # 2) post-process audio: mux heartbeat + ambient + jump sfx on frames
    audio = job.get("audio", {})
    hb = audio.get("heartbeat")
    amb = audio.get("ambient")
    jump = audio.get("jump")
    # If jump events exist, overlay jump sfx at those times (simple approach)
    # Create a base video from frames
    mp4 = out / "preview.mp4"
    ff_cmd = f'{FFMPEG} -y -r 24 -i {out}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {mp4}'
    subprocess.run(ff_cmd, shell=True)
    # now overlay ambient and heartbeat (simple mix)
    final = out / "final_with_audio.mp4"
    if hb or amb:
        # merge amb + hb into one wav
        mix = out / "mix.wav"
        parts = []
        if amb: parts.append(f'-i "{amb}"')
        if hb: parts.append(f'-i "{hb}"')
        # mix filter
        cmd_mix = f'{FFMPEG} -y {" ".join(parts)} -filter_complex "amix=inputs={len(parts)}:duration=shortest" -c:a pcm_s16le "{mix}"'
        subprocess.run(cmd_mix, shell=True)
        cmd_merge = f'{FFMPEG} -y -i "{mp4}" -i "{mix}" -c:v copy -c:a aac -shortest "{final}"'
        subprocess.run(cmd_merge, shell=True)
    else:
        final = mp4
    return {"ok": True, "out": str(final)}
