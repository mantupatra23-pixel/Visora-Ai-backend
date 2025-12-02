# services/wav2lip_service.py
import os
import torch
import subprocess
from pathlib import Path
import uuid
from typing import Dict
import shutil

BASE = Path("wav2lip_repo")
CHECKPOINTS = BASE / "checkpoints"
WAV2LIP_PTH = CHECKPOINTS / "Wav2Lip.pth"
WAV2LIP_GAN_PTH = CHECKPOINTS / "Wav2Lip_gan.pth"
S3FD_PTH = CHECKPOINTS / "s3fd.pth"

JOBS = Path("jobs/wav2lip")
JOBS.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:8]

def _ensure_models():
    if not WAV2LIP_PTH.exists():
        raise FileNotFoundError(f"Wav2Lip model not found: {WAV2LIP_PTH}")
    if not S3FD_PTH.exists():
        raise FileNotFoundError(f"s3fd face detector not found: {S3FD_PTH}")

def prepare_job(video_path: str, audio_path: str | None, consent: bool, options: Dict | None = None):
    if not consent:
        raise PermissionError("User consent required for lipsync/dub operations.")
    j = {
        "job_id": f"wav_{_tid()}",
        "video": video_path,
        "audio": audio_path,
        "options": options or {},
        "status": "queued",
        "out_dir": str(JOBS / f"wav_{_tid()}"),
    }
    Path(j['out_dir']).mkdir(parents=True, exist_ok=True)
    (Path(j['out_dir']) / "job.json").write_text(str(j))
    return j

def run_wav2lip(video_path: str, audio_path: str, out_path: str, use_gan: bool = False):
    """
    This wrapper assumes 'inference.py' exists in wav2lip_repo (official repo inference script).
    It calls the repo's inference script with correct args.
    """
    _ensure_models()
    repo_dir = BASE
    infer_script = repo_dir / "inference.py"
    if not infer_script.exists():
        raise FileNotFoundError(f"Inference script not found: {infer_script}. Clone Wav2Lip repo into {repo_dir}")

    # choose checkpoint
    checkpoint = str(WAV2LIP_GAN_PTH if use_gan and WAV2LIP_GAN_PTH.exists() else WAV2LIP_PTH)

    cmd = [
        "python", str(infer_script),
        "--checkpoint_path", checkpoint,
        "--face", video_path,
        "--audio", audio_path,
        "--outfile", out_path
    ]
    # run subprocess and stream stdout/stderr
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + "\n" + proc.stderr

def merge_audio_video(orig_video: str, new_video: str, final_out: str):
    """
    If generated video already has audio swapped, this step might not be necessary.
    Use ffmpeg to ensure final mux with original video settings or new audio.
    """
    # simple copy (replace audio from new_video if present)
    cmd = f'ffmpeg -y -i "{new_video}" -i "{orig_video}" -map 0:v -map 1:a -c:v copy -c:a aac "{final_out}"'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr
