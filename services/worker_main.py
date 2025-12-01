# services/worker_main.py
import os, subprocess
from pathlib import Path

# start celery worker (assuming tasks package configured)
cmd = "celery -A tasks worker --loglevel=info -Q default"
print("Starting celery worker:", cmd)
subprocess.run(cmd, shell=True)
