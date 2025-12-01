# services/face_reenact.py
"""
Face Reenactment Engine wrapper
- Supports multiple backends: Wav2Lip (audio->lip), SadTalker (audio->full-face), FirstOrder (video->motion)
- Exposes functions:
    - save_target_file(file_bytes, filename) -> saved_path
    - run_wav2lip(target_img_or_video, audio_path, out_path, options) -> runs Wav2Lip CLI/Python
    - run_sadtalker(target_img, audio_path, out_path, options) -> runs SadTalker script
    - run_firstorder(source_image, driving_video, out_path, options) -> runs First-Order Motion Model
- The wrapper calls external repos via subprocess. Adjust paths via env vars.
"""
import os
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(".").resolve()
UPLOADS = ROOT / "uploads" / "face"
OUTDIR = ROOT / "static" / "face_reenact"
OUTDIR.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)

# Set these env vars in your deployment or change defaults
WAV2LIP_PATH = os.getenv("WAV2LIP_PATH", str(ROOT / "wav2lip"))      # repo path
SADTALKER_PATH = os.getenv("SADTALKER_PATH", str(ROOT / "sadtalker"))
FIRSTORDER_PATH = os.getenv("FIRSTORDER_PATH", str(ROOT / "first_order"))

def _task_id():
    return uuid.uuid4().hex[:12]

def save_uploaded_file(file_bytes: bytes, filename: str | None = None) -> str:
    fname = filename or f"file_{_task_id()}"
    dest = UPLOADS / fname
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

def run_wav2lip(target, audio, out_name: Optional[str] = None, fps: int = 25, extra_args: Optional[list] = None) -> Dict:
    """
    target: path to image (jpg/png) or video (mp4)
    audio: path to wav/mp3
    This wrapper assumes Wav2Lip repo has a inference script `inference.py` or `wav2lip.py` (adjust accordingly).
    Example CLI:
      python Wav2Lip/inference.py --checkpoint_path <ckpt> --face <target> --audio <audio> --outfile <out>
    """
    out_name = out_name or f"wav2lip_{_task_id()}.mp4"
    out_path = OUTDIR / out_name
    try:
        ckpt = os.getenv("WAV2LIP_CKPT", str(Path(WAV2LIP_PATH) / "checkpoints" / "wav2lip_gan.pth"))
        cmd = ["python", str(Path(WAV2LIP_PATH) / "inference.py"),
               "--checkpoint_path", ckpt,
               "--face", str(target),
               "--audio", str(audio),
               "--outfile", str(out_path),
               "--fps", str(fps)]
        if extra_args:
            cmd += extra_args
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        returncode = proc.returncode
        return {"ok": returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr, "out": str(out_path) if returncode==0 else None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_sadtalker(target_img, audio, out_name: Optional[str] = None, extra_args: Optional[list] = None) -> Dict:
    """
    SadTalker wrapper.
    Example CLI (depends on sadtalker repo layout):
      python sadtalker/inference.py --config cfg --checkpoint ckpt --source_image target.png --audio audio.wav --output out.mp4
    Adjust commands to your installed repo's CLI.
    """
    out_name = out_name or f"sadtalker_{_task_id()}.mp4"
    out_path = OUTDIR / out_name
    try:
        ckpt = os.getenv("SADTALKER_CKPT", str(Path(SADTALKER_PATH) / "checkpoints" / "sadtalker.pth"))
        cmd = ["python", str(Path(SADTALKER_PATH) / "inference.py"),
               "--checkpoint", ckpt,
               "--source_image", str(target_img),
               "--audio", str(audio),
               "--output", str(out_path)]
        if extra_args:
            cmd += extra_args
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
        returncode = proc.returncode
        return {"ok": returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr, "out": str(out_path) if returncode==0 else None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_firstorder(source_img, driving_video, out_name: Optional[str] = None, extra_args: Optional[list] = None) -> Dict:
    """
    First-Order Motion Model wrapper (video-driven motion).
    Example CLI:
      python demo.py --config config/vox-256.yaml --driving_video driving.mp4 --source_image source.png --checkpoint checkpoints/vox.pth --relative --adapt_scale
    """
    out_name = out_name or f"fofm_{_task_id()}.mp4"
    out_path = OUTDIR / out_name
    try:
        ckpt = os.getenv("FOFM_CKPT", str(Path(FIRSTORDER_PATH) / "checkpoints" / "vox.pth"))
        cmd = ["python", str(Path(FIRSTORDER_PATH) / "demo.py"),
               "--config", str(Path(FIRSTORDER_PATH) / "config" / "config.yaml"),
               "--driving_video", str(driving_video),
               "--source_image", str(source_img),
               "--checkpoint", ckpt,
               "--relative", "--adapt_scale",
               "--out", str(out_path)]
        if extra_args:
            cmd += extra_args
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
        returncode = proc.returncode
        return {"ok": returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr, "out": str(out_path) if returncode==0 else None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
