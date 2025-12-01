# services/sadtalker_engine.py
import os
import subprocess
from pathlib import Path
import hashlib
import time

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

class SadTalkerEngine:
    """
    This is a lightweight wrapper that calls the SadTalker repo's inference script (CLI).
    Assumes you cloned SadTalker into `sadtalker_repo` (or set repo_path) and placed checkpoints.
    """
    def __init__(self, repo_path: str = "sadtalker_repo", checkpoints_dir: str | None = None, python_bin: str = "python"):
        self.repo = Path(repo_path)
        self.python = python_bin
        self.checkpoints_dir = Path(checkpoints_dir) if checkpoints_dir else (self.repo / "checkpoints")
        if not self.repo.exists():
            raise RuntimeError(f"SadTalker repo not found at: {self.repo}")
        if not self.checkpoints_dir.exists():
            # not fatal — user may place checkpoints later, but warn
            print(f"[Warn] checkpoints directory not found: {self.checkpoints_dir}. Place required models there.")

    def _safe_name(self, seed: str):
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

    def generate(self, 
                 source_image: str,       # path to source face image (jpg/png)
                 audio_path: str | None,  # path to audio (wav/mp3) OR None if using motion-only
                 driver_video_or_npy: str | None = None,  # optional driving video or motion file
                 output_name: str | None = None,
                 extra_args: list | None = None
                 ) -> str:
        """
        Calls the SadTalker inference command.
        - source_image: face image used as source identity
        - audio_path: driving audio to lip-sync (optional depending on repo)
        - driver_video_or_npy: optional driving video / motion descriptor (optional)
        - output: returns path to generated video (mp4)
        """

        if not Path(source_image).exists():
            raise FileNotFoundError("Source image not found: " + source_image)
        if audio_path and not Path(audio_path).exists():
            raise FileNotFoundError("Audio not found: " + audio_path)

        seed = f"{source_image}-{audio_path}-{time.time()}"
        out_name = output_name or f"sadtalker_{self._safe_name(seed)}.mp4"
        out_path = OUT / out_name

        # Build base command — NOTE: inference.py name/path may differ per repo — check your repo!
        # This wrapper expects an inference script at sadtalker_repo/inference.py that supports:
        # --source_image, --audio, --driving_video, --output
        cmd = [self.python, str(self.repo / "inference.py"),
               "--source_image", str(source_image),
               "--output", str(out_path)]

        if audio_path:
            cmd += ["--audio", str(audio_path)]
        if driver_video_or_npy:
            cmd += ["--driving_video", str(driver_video_or_npy)]

        # add checkpoints dir if repo supports it (some repos use --checkpoint_dir or env)
        # If extra_args provided, append them
        if extra_args:
            cmd += extra_args

        # run
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # include stdout/stderr for debugging
            raise RuntimeError(f"SadTalker inference failed.\nReturn code: {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        if not out_path.exists():
            raise RuntimeError("SadTalker finished but output file not found: " + str(out_path))

        return str(out_path)
