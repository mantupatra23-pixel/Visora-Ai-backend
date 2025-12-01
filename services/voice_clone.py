# services/voice_clone.py
"""
Voice Cloning wrapper service.

Design:
- Uses an external Voice Cloning tool (default: Real-Time-Voice-Cloning repo)
- Provides functions:
    - save_uploaded_sample(fileobj) -> saved_path
    - create_voice_clone(samples_list, speaker_id) -> runs training/encoder step -> stores speaker embedding / model
    - synthesize_text(speaker_id, text, out_filename) -> returns path to synthesized audio

Implementation notes:
- This file calls external scripts via subprocess. Adjust paths to your RTVC installation.
- Heavy operations MUST run on GPU machine. Consider running in Celery worker.
"""

import os
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

ROOT = Path(".").resolve()
UPLOADS = ROOT / "uploads" / "voice_samples"
VOICES = ROOT / "models" / "voices"   # store speaker embeddings / metadata here
SYNTH_OUT = ROOT / "static" / "voice_clones"
for p in (UPLOADS, VOICES, SYNTH_OUT):
    p.mkdir(parents=True, exist_ok=True)

# Path to your Real-Time-Voice-Cloning repo (adjust)
RTVC_PATH = os.getenv("RTVC_PATH", str(ROOT / "rtvc"))

def _safe_id():
    return uuid.uuid4().hex[:12]

def save_uploaded_sample(file_bytes: bytes, filename: str | None = None) -> str:
    """
    Save uploaded audio bytes to UPLOADS folder. Returns saved path (str).
    """
    fname = filename or f"sample_{_safe_id()}.wav"
    dest = UPLOADS / fname
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

def create_voice_clone_from_samples(sample_paths: List[str], speaker_id: Optional[str] = None, overwrite: bool = False, extra_args: List[str] = None) -> Dict:
    """
    High-level wrapper to create/store a speaker clone.
    Strategy (RTVC typical approach):
      - Use encoder to compute speaker embedding from one or multiple wavs
      - Save embedding file under models/voices/<speaker_id>.npy (or store metadata)
    Note: Full "training" of TTS is heavy. RTVC approach computes speaker embedding + uses pretrained TTS to synthesize (few-shot).
    """
    sid = speaker_id or _safe_id()
    speaker_dir = VOICES / sid
    if speaker_dir.exists() and not overwrite:
        return {"ok": False, "msg": "speaker_exists", "speaker_id": sid}
    # create dir
    if speaker_dir.exists() and overwrite:
        shutil.rmtree(speaker_dir)
    speaker_dir.mkdir(parents=True, exist_ok=True)
    # copy samples to speaker_dir/samples/
    sp_samples_dir = speaker_dir / "samples"
    sp_samples_dir.mkdir(parents=True, exist_ok=True)
    for p in sample_paths:
        src = Path(p)
        if src.exists():
            shutil.copy(src, sp_samples_dir / src.name)
    # compute embedding using RTVC encoder (example script)
    # RTVC repo usually exposes: encoder/encoder.py which has embed_utterance API
    # Here we will call a helper Python script inside RTVC that loads encoder and produces embedding file
    embed_out = speaker_dir / "embedding.npy"
    try:
        # example: python rtvc/encoder_script.py --input_dir models/voices/<id>/samples --out embedding.npy
        cmd = ["python", str(Path(RTVC_PATH) / "encoder_script.py"),
               "--input_dir", str(sp_samples_dir),
               "--out", str(embed_out)]
        if extra_args:
            cmd += extra_args
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return {"ok": False, "error": "encoder_failed", "stdout": proc.stdout, "stderr": proc.stderr}
        # store metadata
        meta = {"speaker_id": sid, "samples": [str(x) for x in sp_samples_dir.glob("*")], "embedding": str(embed_out)}
        (speaker_dir / "meta.json").write_text(str(meta))
        return {"ok": True, "speaker_id": sid, "meta": meta}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def synthesize_text_with_speaker(speaker_id: str, text: str, out_filename: Optional[str] = None, tts_args: List[str] = None) -> Dict:
    """
    Uses the pretrained TTS model + speaker embedding to synthesize audio.
    Example RTVC usage: python demo_cli.py --text "Hello" --speaker_embedding models/voices/<id>/embedding.npy --outfile out.wav
    Adapt the command to your RTVC demo script.
    """
    speaker_dir = VOICES / speaker_id
    if not speaker_dir.exists():
        return {"ok": False, "error": "speaker_not_found"}
    embed = speaker_dir / "embedding.npy"
    if not embed.exists():
        return {"ok": False, "error": "embedding_missing"}
    out_name = out_filename or f"tts_{speaker_id}_{_safe_id()}.wav"
    out_path = SYNTH_OUT / out_name
    try:
        # example CLI for RTVC TTS demo (adjust to your repo's script)
        cmd = ["python", str(Path(RTVC_PATH) / "synthesize_cli.py"),
               "--text", text,
               "--speaker_embedding", str(embed),
               "--outfile", str(out_path)]
        if tts_args:
            cmd += tts_args
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return {"ok": False, "error": "synthesis_failed", "stdout": proc.stdout, "stderr": proc.stderr}
        return {"ok": True, "speaker_id": speaker_id, "text": text, "audio_path": str(out_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
