# services/wav2lip_service.py
"""
Wav2Lip service wrapper
- Searches for the Wav2Lip repo in a few common locations or uses WAV2LIP_REPO env var
- Validates presence of required checkpoints
- Prepares job folders and job metadata
- Calls inference.py as a subprocess and returns rc + combined stdout/stderr
- Provides a helper to merge audio/video using ffmpeg
"""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
import uuid
from typing import Dict, Optional, Tuple, List

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Candidate locations to search for the Wav2Lip repo
CANDIDATE_REPOS: List[Path] = [
    Path("wav2lip_repo"),
    Path("Wav2Lip"),
    Path("/opt/wav2lip"),
    Path.home() / "wav2lip_repo",
    Path.home() / "Wav2Lip",
]

CHECKPOINT_REL = Path("checkpoints")
MODEL_FILES = ["Wav2Lip.pth", "Wav2Lip_gan.pth", "s3fd.pth"]

# Where we create job folders (relative to current working dir)
JOBS = Path("jobs/wav2lip")
JOBS.mkdir(parents=True, exist_ok=True)

# Small helper for unique ids
def _tid() -> str:
    return uuid.uuid4().hex[:8]

def find_repo_and_infer() -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """
    Search common candidate paths for the inference.py and checkpoints.
    Returns (repo_path, inference_py_path, checkpoints_path) or (None, None, None)
    """
    # Check explicit environment variable first
    env_repo = os.getenv("WAV2LIP_REPO")
    if env_repo:
        p = Path(env_repo)
        infer = p / "inference.py"
        ck = p / "checkpoints"
        if infer.exists() and ck.exists():
            LOG.info("Found Wav2Lip via WAV2LIP_REPO: %s", p)
            return p, infer, ck

    for repo in CANDIDATE_REPOS:
        infer = repo / "inference.py"
        ck = repo / "checkpoints"
        # Common forks sometimes keep repo content nested under "Wav2Lip"
        nested_infer = repo / "Wav2Lip" / "inference.py"
        nested_ck = repo / "Wav2Lip" / "checkpoints"
        if infer.exists() and ck.exists():
            LOG.info("Found Wav2Lip repo: %s", repo)
            return repo, infer, ck
        if nested_infer.exists() and nested_ck.exists():
            LOG.info("Found nested Wav2Lip repo: %s", repo / "Wav2Lip")
            return repo / "Wav2Lip", nested_infer, nested_ck

    LOG.warning("Wav2Lip repo not found in candidate locations.")
    return None, None, None

def ensure_models(checkpoints: Path) -> None:
    """
    Ensure required model files exist in the checkpoints folder.
    Raises FileNotFoundError if any are missing.
    """
    missing = [m for m in MODEL_FILES if not (checkpoints / m).exists()]
    if missing:
        raise FileNotFoundError(f"Missing model files in {checkpoints}: {missing}")
    LOG.info("All required model files present in %s", checkpoints)

def prepare_job(video_path: str, audio_path: Optional[str], consent: bool, options: Optional[Dict] = None) -> Dict:
    """
    Prepare a job object and create output directory + job.json
    """
    if not consent:
        raise PermissionError("User consent required for lipsync/dub operations.")
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    job_id = f"wav_{_tid()}"
    out_dir = JOBS / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    job = {
        "job_id": job_id,
        "video": video_path,
        "audio": audio_path,
        "options": options or {},
        "status": "queued",
        "out_dir": str(out_dir),
    }
    (out_dir / "job.json").write_text(str(job))
    LOG.info("Prepared job %s -> %s", job_id, out_dir)
    return job

def run_wav2lip_raw(repo_inference_py: Path, checkpoint_path: Path, face_video: str, audio: str, out_file: str, timeout: Optional[int] = None) -> Tuple[int, str]:
    """
    Call inference.py directly using given repo path and chosen checkpoint.
    Returns (returncode, combined_stdout_stderr)
    """
    cmd = [
        "python", str(repo_inference_py),
        "--checkpoint_path", str(checkpoint_path),
        "--face", str(face_video),
        "--audio", str(audio),
        "--outfile", str(out_file),
    ]
    LOG.info("Running Wav2Lip: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = proc.stdout + "\n" + proc.stderr
        LOG.info("Wav2Lip finished rc=%s", proc.returncode)
        return proc.returncode, out
    except subprocess.TimeoutExpired as e:
        LOG.error("Wav2Lip timed out after %s seconds", timeout)
        return 124, f"Timeout after {timeout}s\n{e}"

def run_wav2lip(video_path: str, audio_path: str, out_path: str, use_gan: bool = False, timeout: Optional[int] = None) -> Tuple[int, str]:
    """
    High-level helper: locate repo, validate models, and run inference.
    """
    repo, infer_py, ck = find_repo_and_infer()
    if not repo or not infer_py or not ck:
        raise FileNotFoundError("Wav2Lip repo or inference.py not found. Please set WAV2LIP_REPO or place the repo in a candidate location.")
    ensure_models(ck)

    chosen = ck / ("Wav2Lip_gan.pth" if use_gan and (ck / "Wav2Lip_gan.pth").exists() else "Wav2Lip.pth")
    return run_wav2lip_raw(infer_py, chosen, video_path, audio_path, out_path, timeout=timeout)

def merge_audio_video(orig_video: str, new_video: str, final_out: str, timeout: int = 60) -> Tuple[int, str]:
    """
    Use ffmpeg to take video from new_video and audio from orig_video.
    Returns (returncode, combined stdout+stderr)
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(new_video),
        "-i", str(orig_video),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        str(final_out),
    ]
    LOG.info("Merging audio/video via ffmpeg: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = proc.stdout + "\n" + proc.stderr
        LOG.info("ffmpeg finished rc=%s", proc.returncode)
        return proc.returncode, out
    except subprocess.TimeoutExpired as e:
        LOG.error("ffmpeg timed out after %s seconds", timeout)
        return 124, f"Timeout after {timeout}s\n{e}"

def safe_run_example(video: str, audio: str, use_gan: bool = False) -> Dict:
    """
    Example high-level flow:
    - create a temporary working dir
    - call Wav2Lip
    - merge audio if needed
    - return result dict
    """
    job = prepare_job(video, audio, consent=True, options={"use_gan": use_gan})
    out_dir = Path(job["out_dir"])
    tmp_out = out_dir / f"{job['job_id']}_raw.mp4"
    final_out = out_dir / f"{job['job_id']}_final.mp4"

    rc, out = run_wav2lip(video, audio, str(tmp_out), use_gan=use_gan, timeout=1800)
    result = {"rc": rc, "log": out, "raw": str(tmp_out)}

    if rc != 0:
        LOG.error("run_wav2lip failed: rc=%s", rc)
        job["status"] = "failed"
        (out_dir / "result.txt").write_text(out)
        return {"job": job, "result": result}

    # merge audio (ensure final mux with original audio)
    m_rc, m_out = merge_audio_video(video, str(tmp_out), str(final_out))
    result["merge_rc"] = m_rc
    result["merge_log"] = m_out
    if m_rc == 0:
        job["status"] = "done"
        result["final"] = str(final_out)
    else:
        job["status"] = "merged_failed"
        result["final"] = str(tmp_out)

    (out_dir / "result.txt").write_text(str(result))
    LOG.info("Job %s finished status=%s", job["job_id"], job["status"])
    return {"job": job, "result": result}

# If you want to allow running the example from command line for quick tests:
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Small wrapper to run Wav2Lip from a local repo")
    parser.add_argument("-v", "--video", required=True, help="input face video")
    parser.add_argument("-a", "--audio", required=True, help="input audio file")
    parser.add_argument("-o", "--out", default=None, help="output file (optional)")
    parser.add_argument("--gan", action="store_true", help="use GAN checkpoint if present")
    args = parser.parse_args()

    out_path = args.out or f"out_{_tid()}.mp4"
    try:
        res = safe_run_example(args.video, args.audio, use_gan=args.gan)
        print("RESULT:", res)
    except Exception as e:
        LOG.exception("Exception running Wav2Lip wrapper: %s", e)
        raise
