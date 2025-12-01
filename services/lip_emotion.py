# services/lip_emotion.py
"""
Lip-Emotion Fusion Engine wrapper
Pipeline (high level):
- Input: audio_path OR text + voice_spec + reference_face (image/glb)
- Step1: If text -> TTS (external TTS engine or offline) -> produce wav
- Step2: Emotion mapping (map emotional label to prosody + facial action params)
- Step3: Run face animation model (Wav2Lip / SadTalker variant) to produce talking video or landmark sequence
- Step4: Optional smoothing, head/eye micro-motions, emotion blend overlays
- Step5: Export: video (mp4), landmarks (npz/json), blendshapes (npy) or FBX via Blender retarget

Notes:
- This wrapper expects external model CLIs/scripts available in repo or system.
- Provide example minimal implementations using Wav2Lip (for lipsync) + simple head motion heuristics.
"""
import os, json, uuid, subprocess, shlex, tempfile
from pathlib import Path
from typing import Dict, Any

ROOT = Path(".").resolve()
UPLOADS = ROOT / "uploads" / "lip_emotion"
OUT = ROOT / "static" / "lip_emotion"
MODEL_DIR = ROOT / "models" / "lip_emotion"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def _task_id():
    return uuid.uuid4().hex[:12]

# ---------- helpers ----------
def save_upload(file_bytes: bytes, filename: str | None = None) -> str:
    fname = filename or f"input_{_task_id()}"
    dest = UPLOADS / fname
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

def run_cmd(cmd: str, timeout: int = 3600) -> Dict[str,Any]:
    print("RUN:", cmd)
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}

# ---------- TTS (simple wrapper; you can plug any TTS) ----------
def tts_offline(text: str, out_wav: str, voice="default"):
    """
    Minimal placeholder: expects a local TTS CLI (espeak, TTS, or other).
    For production plug: Coqui-TTS / Edge / Google etc.
    Example: using pyttsx3 is possible but lower quality.
    """
    # Example: use Coqui-TTS CLI if installed (assumes `tts` binary)
    if shutil.which("tts"):
        cmd = f'tts --text {shlex.quote(text)} --out_path {shlex.quote(out_wav)}'
        return run_cmd(cmd, timeout=120)
    # fallback: use espeak (mono wav)
    cmd = f'espeak {shlex.quote(text)} --stdout > {shlex.quote(out_wav)}'
    return run_cmd(cmd, timeout=30)

# ---------- Emotion mapping ----------
EMOTION_PRESETS = {
    "neutral": {"head_nod":0.02, "eye_blink_rate":0.08, "brow_raise":0.0, "mouth_open_scale":1.0},
    "happy": {"head_nod":0.06, "eye_blink_rate":0.12, "brow_raise":0.05, "mouth_open_scale":1.05},
    "sad": {"head_nod":0.01, "eye_blink_rate":0.05, "brow_raise":-0.03, "mouth_open_scale":0.9},
    "angry": {"head_nod":0.02, "eye_blink_rate":0.06, "brow_raise":-0.1, "mouth_open_scale":1.02}
}

def map_emotion_to_params(emotion: str):
    return EMOTION_PRESETS.get(emotion, EMOTION_PRESETS["neutral"])

# ---------- Wav2Lip / SadTalker runner (example) ----------
def run_wav2lip(reference_image: str, wav_path: str, out_video: str, checkpoints_dir: str = None):
    """
    Expects wav2lip implementation available as CLI or python script in repo:
    Example command:
    python inference/wav2lip.py --checkpoint_path <ckpt> --face <face.jpg> --audio <audio.wav> --outfile <out.mp4>
    """
    ck = checkpoints_dir or str(MODEL_DIR / "wav2lip.pth")
    # choose a typical wav2lip CLI (adjust path if your repo differs)
    script = ROOT / "extern" / "wav2lip" / "inference.py"
    if script.exists():
        cmd = f"python {shlex.quote(str(script))} --checkpoint {shlex.quote(ck)} --face {shlex.quote(reference_image)} --audio {shlex.quote(wav_path)} --outfile {shlex.quote(out_video)}"
        return run_cmd(cmd, timeout=7200)
    # fallback: if no script, error
    return {"ok": False, "error": "wav2lip_not_found", "expected": str(script)}

def run_sadtalker(reference_image: str, wav_path: str, out_video: str, model_path: str | None = None):
    """
    Example wrapper for SadTalker variant that produces more expressive face motion.
    Assumes repository in extern/sadtalker and a python entrypoint script 'inference.py'
    """
    script = ROOT / "extern" / "sadtalker" / "inference.py"
    ck = model_path or str(MODEL_DIR / "sadtalker.pth")
    if script.exists():
        cmd = f"python {shlex.quote(str(script))} --checkpoint {shlex.quote(ck)} --img {shlex.quote(reference_image)} --audio {shlex.quote(wav_path)} --out {shlex.quote(out_video)}"
        return run_cmd(cmd, timeout=7200)
    return {"ok": False, "error": "sadtalker_not_found", "expected": str(script)}

# ---------- Postprocess: add micro head/eye motion and emotion blend ----------
def apply_emotion_postproc(in_video: str, out_video: str, emotion_params: dict):
    """
    Simple postproc: overlay small head rotations and blink events.
    Implemented as a placeholder that currently copies the file.
    For real: decode frames, apply facial landmarks transform over frames (openCV + dlib) and re-encode.
    """
    # fallback: just copy
    try:
        import shutil
        shutil.copy(in_video, out_video)
        return {"ok": True, "out": out_video}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---------- Main high-level function ----------
def create_lip_emotion_job(input_image: str, audio_path: str | None = None, text: str | None = None, emotion: str = "neutral", engine: str = "sadtalker", out_name: str | None = None):
    """
    - If text provided, TTS to wav (uses tts_offline)
    - Run chosen model (sadtalker or wav2lip)
    - Postprocess with emotion params
    - Returns output paths
    """
    tid = _task_id()
    out_name = out_name or f"lip_em_{tid}.mp4"
    out_tmp = OUT / f"tmp_{tid}.mp4"
    out_final = OUT / out_name

    # 1) ensure audio
    if text and not audio_path:
        wav = str(OUT / f"tts_{tid}.wav")
        t = tts_offline(text, wav)
        if not t.get("ok"):
            return {"ok": False, "error": "tts_failed", "detail": t}
        audio_path = wav
    if not audio_path:
        return {"ok": False, "error": "no_audio"}

    # 2) run model
    if engine == "wav2lip":
        res = run_wav2lip(input_image, audio_path, str(out_tmp))
    else:
        res = run_sadtalker(input_image, audio_path, str(out_tmp))
    if not res.get("ok"):
        return {"ok": False, "error": "model_failed", "detail": res}

    # 3) postprocess emotion
    params = map_emotion_to_params(emotion)
    post = apply_emotion_postproc(str(out_tmp), str(out_final), params)
    if not post.get("ok"):
        return {"ok": False, "error": "postproc_failed", "detail": post}
    return {"ok": True, "task_id": tid, "out_video": str(out_final), "tmp": str(out_tmp), "emotion": emotion}
