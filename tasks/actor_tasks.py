# tasks/actor_tasks.py
from celery import Celery
import json, subprocess, shlex, os
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('actor', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def bake_actor(self, phoneme_file, blend_in, obj_name):
    script = "blender_scripts/lipsync_baker.py"
    cmd = f"{BLENDER_BIN} --background {blend_in} --python {script} -- {obj_name} {phoneme_file} output.blend"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok":p.returncode==0, "stdout":p.stdout, "stderr":p.stderr}
