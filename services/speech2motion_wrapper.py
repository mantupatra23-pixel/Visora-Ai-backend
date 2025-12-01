# services/speech2motion_wrapper.py
import os, shlex, subprocess, uuid
from pathlib import Path

ROOT = Path(".").resolve()
EXTERN = ROOT / "extern" / "speech2motion"
MODEL_DIR = ROOT / "models" / "speech2motion"
OUT = ROOT / "static" / "speech2motion"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def infer_speech2motion(wav_path: str, speaker_profile: dict | None = None, checkpoint: str | None = None, out_npz: str | None = None, device: str = "cuda:0"):
    """
    Expects an inference script at extern/speech2motion/inference.py which:
      python inference.py --audio <wav> --ckpt <ckpt> --out <out.npz> --device cuda:0 --profile '{"energy":0.8}'
    Returns dict with ok & out path or error.
    """
    infer_script = EXTERN / "inference.py"
    if not infer_script.exists():
        return {"ok": False, "error": "speech2motion_infer_missing", "expected": str(infer_script)}
    out_npz = out_npz or str(OUT / f"motion_{_tid()}.npz")
    ck = checkpoint or str(MODEL_DIR / "speech2motion.pth")
    profile_arg = shlex.quote(str(speaker_profile)) if speaker_profile else shlex.quote("{}")
    cmd = f"python {shlex.quote(str(infer_script))} --audio {shlex.quote(wav_path)} --ckpt {shlex.quote(ck)} --out {shlex.quote(out_npz)} --device {shlex.quote(device)} --profile {profile_arg}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "out": out_npz}
