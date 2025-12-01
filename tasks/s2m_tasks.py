# tasks/s2m_tasks.py
from celery import Celery
import os, shlex, subprocess
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery('s2m', broker=BROKER, backend=BROKER)

SCRIPT = str(Path.cwd() / "extern" / "speech2motion" / "inference.py")

@app.task(bind=True, time_limit=10800)
def run_s2m(self, wav_path, ckpt, out_npz, device="cuda:0", profile=None):
    profile_arg = str(profile) if profile else "{}"
    cmd = f"python {shlex.quote(SCRIPT)} --audio {shlex.quote(wav_path)} --ckpt {shlex.quote(ckpt)} --out {shlex.quote(out_npz)} --device {shlex.quote(device)} --profile {shlex.quote(profile_arg)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10800)
    return {"ok": p.returncode==0, "stdout": p.stdout[:1000], "stderr": p.stderr[:1000], "out": out_npz}
