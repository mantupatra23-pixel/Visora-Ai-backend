# services/lipsync_engine.py
import os
import subprocess
from pathlib import Path
import hashlib
import time

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

def _safe_name(seed: str):
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

class LipSyncEngine:
    def __init__(self, repo_path="wav2lip_repo", model_path="models/wav2lip/wav2lip_gan.pth"):
        self.repo = Path(repo_path)
        self.model = Path(model_path)

        if not self.repo.exists():
            raise RuntimeError("Wav2Lip repo not found at: " + str(self.repo))

        if not self.model.exists():
            raise RuntimeError("wav2lip_gan.pth not found.")

    def lipsync(self, image_path: str, audio_path: str, output_name=None):
        if not Path(image_path).exists():
            raise FileNotFoundError("Image missing: " + image_path)
        if not Path(audio_path).exists():
            raise FileNotFoundError("Audio missing: " + audio_path)

        out_name = output_name or f"lipsync_{_safe_name(image_path+audio_path+str(time.time()))}.mp4"
        out_path = OUT / out_name

        cmd = [
            "python", str(self.repo / "inference.py"),
            "--checkpoint_path", str(self.model),
            "--face", image_path,
            "--audio", audio_path,
            "--outfile", str(out_path)
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.returncode != 0:
            raise RuntimeError(f"Wav2Lip failed:\n{p.stderr}\n{p.stdout}")

        return str(out_path)
