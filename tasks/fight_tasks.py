# tasks/fight_tasks.py
from celery import Celery, chain
import os, shlex, subprocess, json
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('fight', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def plan_fight(self, script_line, length_sec=6, fps=24):
    from services.fight_planner import build_choreography, save_job
    job = build_choreography(script_line, length_sec=length_sec, fps=fps)
    # ensure output_path exists (use same job json)
    job['output_path'] = str(Path("jobs/fight") / (job['job_id'] + ".json"))
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job['output_path']

@app.task(bind=True)
def run_baker(self, jobfile):
    outdir = Path("jobs/fight") / (Path(jobfile).stem + "_out")
    outdir.mkdir(parents=True, exist_ok=True)
    script = Path("blender_scripts") / "fight_baker.py"
    cmd = f"{BLENDER_BIN} --background --python {shlex.quote(str(script))} -- {shlex.quote(str(jobfile))} {shlex.quote(str(outdir))}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "outdir": str(outdir)}

@app.task(bind=True)
def post_process(self, outdir):
    # simple: mux frames to mp4 and add hit SFX on impact frames
    outdir = Path(outdir)
    # check impacts
    impacts_file = outdir / "impacts.json"
    sfx_file = "assets/sfx/hit.wav"
    # create timeline mp4
    mp4 = outdir / "final_preview.mp4"
    cmd = f"ffmpeg -y -r 24 -i {outdir}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {mp4}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok": p.returncode==0, "mp4": str(mp4)}

@app.task(bind=True)
def full_pipeline(self, script_line, length_sec=6, fps=24):
    # chain: plan -> baker -> post
    res = plan_fight.run(script_line, length_sec, fps)
    jobfile = res
    baker = run_baker.run(jobfile)
    outdir = baker.get("outdir")
    post = post_process.run(outdir)
    return {"ok": True, "outdir": outdir}
