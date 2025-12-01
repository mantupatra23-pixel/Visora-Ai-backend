# services/realtime_pipeline.py
"""
Simple chunked realtime pipeline (HTTP+WS based).
- Accepts short audio chunks (16kHz mono ~0.5-1s) via WebSocket or HTTP POST
- Runs a fast lightweight model (requires optimized runtime)
- Returns landmarks or short mp4 chunk for client to render ASAP

This is a simplistic, non-production example.
"""
import os, uuid, base64, tempfile, subprocess, shlex
from pathlib import Path
ROOT = Path(".").resolve()
RT_TMP = ROOT / "tmp" / "realtime"
RT_TMP.mkdir(parents=True, exist_ok=True)

def process_chunk_fast(face_image_path: str, audio_chunk_path: str, out_chunk_path: str):
    # Try a very fast shallow wav2lip inference (if you compiled optimized variant)
    script = ROOT / "extern" / "wav2lip" / "inference_fast.py"
    if script.exists():
        cmd = f"python {shlex.quote(str(script))} --face {shlex.quote(face_image_path)} --audio {shlex.quote(audio_chunk_path)} --outfile {shlex.quote(out_chunk_path)} --fast"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"ok": p.returncode==0, "stdout":p.stdout, "stderr":p.stderr}
    # fallback: return error
    return {"ok": False, "error": "no_fast_inference_available"}
