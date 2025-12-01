# services/voice2anim.py
"""
Voice-to-Animation Engine

Functions:
- save_audio(bytes, filename) -> path
- extract_audio_features(wav_path) -> dict {frames:[{t,pitch,energy,phoneme?}], fps}
- predict_motion_from_audio(features, profile, mode='fast'|'hq') -> motion_dict (frames -> joints)
- export_bvh_from_motion(motion_dict, out_path)
- run_full_pipeline(wav_path, profile, mode, out_name)

Notes:
- fast mode uses heuristics + small learned mapping (can be implemented as lightweight sklearn/torch model)
- hq mode expects extern model in extern/speech2motion or models dir
- For production run heavy ops in Celery GPU workers
"""
import os, json, uuid, subprocess, math
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
ROOT = Path(".").resolve()
UPLOADS = ROOT / "uploads" / "voice2anim"
OUT = ROOT / "static" / "voice2anim"
MODEL_DIR = ROOT / "models" / "voice2anim"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def _task_id(): return uuid.uuid4().hex[:10]

def save_audio(file_bytes: bytes, filename: str | None = None) -> str:
    fname = filename or f"voice_{_task_id()}.wav"
    dest = UPLOADS / fname
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

# ----------------------------
# 1) Feature extraction (pitch, energy, simple phoneme boundaries)
# ----------------------------
def extract_audio_features(wav_path: str, hop_ms: int = 40):
    """
    Returns frames with timestamp, pitch (Hz or 0), energy (RMS), and optionally phoneme label (if align available).
    Lightweight implementation using librosa (pitch via pyin) and RMS.
    """
    try:
        import librosa
    except Exception as e:
        return {"ok": False, "error": "librosa_missing", "msg": str(e)}
    y, sr = librosa.load(wav_path, sr=16000)
    hop = int(hop_ms/1000 * sr)
    # energy
    rms = librosa.feature.rms(y=y, frame_length=hop*2, hop_length=hop)[0]
    # pitch (pyin)
    try:
        f0, voiced_flag, voiced_prob = librosa.pyin(y, fmin=50, fmax=800, sr=sr, frame_length=hop*2, hop_length=hop)
        f0 = np.nan_to_num(f0).tolist()
    except Exception:
        f0 = [0.0]*len(rms)
    frames = []
    for i in range(len(rms)):
        t = round((i*hop)/sr, 4)
        frames.append({"t": t, "pitch": float(f0[i]), "energy": float(rms[i])})
    return {"ok": True, "fps": round(1000/hop_ms,2), "frames": frames, "sr": sr}

# ----------------------------
# 2) Fast heuristic predictor (rule-based + small mapping)
# ----------------------------
def predict_motion_fast(features: Dict, profile: Dict | None = None):
    """
    Very simple mapping:
    - high energy -> larger arm gestures
    - rising pitch -> head tilt up / eyebrows up
    - low energy -> small subtle gestures
    Output: per-frame motion dictionary for joints: hip, spine, neck, head_rot, left_shoulder, right_shoulder
    Values are small floats; later converted to BVH positions/rotations.
    """
    frames = features.get("frames", [])
    motion = []
    for f in frames:
        e = f.get("energy", 0.0)
        p = f.get("pitch", 0.0)
        # normalize energy
        En = min(1.0, e * 50.0)  # heuristic (tune per data)
        # pitch impact
        pitch_factor = 0.0 if p<=0 else min(1.0, (p-100)/400)
        # gesture magnitude
        mag = En * (0.5 + 0.5 * pitch_factor)
        # random micro variation seeded by time for deterministic output
        seed = int((f['t']*1000) % 9973)
        rand = ( (seed * 9301 + 49297) % 233280 ) / 233280.0
        # produce joint values (rotation in degrees)
        frame_motion = {
            "t": f["t"],
            "hip_y": 0.0,
            "spine_bend": mag * 5.0 * (0.5+rand),
            "neck_tilt": (pitch_factor-0.2)*8.0,
            "head_nod": mag*6.0*rand,
            "left_shoulder_up": mag*12.0*(0.5+rand),
            "right_shoulder_up": mag*8.0*(0.5+1-rand),
            "left_arm_swing": mag*20.0*rand,
            "right_arm_swing": mag*20.0*(1-rand)
        }
        motion.append(frame_motion)
    return {"ok": True, "motion": motion}

# ----------------------------
# 3) High-quality predictor (calls extern model if available)
# ----------------------------
def predict_motion_hq(wav_path: str, out_npz: str | None = None, model_name: str | None = None):
    """
    This function expects an external Speech2Motion model under extern/speech2motion with an inference script.
    Example:
      python extern/speech2motion/inference.py --audio file.wav --out out.npz --checkpoint <ckpt>
    Returns {"ok":True, "out":out_npz}
    """
    script = ROOT / "extern" / "speech2motion" / "inference.py"
    if not script.exists():
        return {"ok": False, "error": "speech2motion_missing", "expected": str(script)}
    out_npz = out_npz or str(OUT / f"motion_{_task_id()}.npz")
    model_ckpt = str(MODEL_DIR / (model_name or "speech2motion.pth"))
    cmd = f"python {str(script)} --audio {str(wav_path)} --out {str(out_npz)} --checkpoint {str(model_ckpt)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "out": out_npz}

# ----------------------------
# 4) Convert motion to BVH (simple exporter)
# ----------------------------
def export_bvh_simple(motion_list: List[Dict], out_path: str):
    """
    Create a minimal BVH with root translation and a few rotation channels for neck/head/arms.
    This is simplified — for production use retarget in Blender using JSON -> bone transforms.
    """
    try:
        lines = []
        lines.append("HIERARCHY")
        lines.append("ROOT Hips")
        lines.append("{")
        lines.append("\tOFFSET 0.00 0.00 0.00")
        lines.append("\tCHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation")
        # create a minimal TWO children for simplicity
        lines.append("\tJOINT Spine")
        lines.append("\t{")
        lines.append("\t\tOFFSET 0.00 10.00 0.00")
        lines.append("\t\tCHANNELS 3 Zrotation Yrotation Xrotation")
        lines.append("\t\tJOINT Neck")
        lines.append("\t\t{")
        lines.append("\t\t\tOFFSET 0.00 8.00 0.00")
        lines.append("\t\t\tCHANNELS 3 Zrotation Yrotation Xrotation")
        lines.append("\t\t\tEnd Site")
        lines.append("\t\t\t{")
        lines.append("\t\t\t\tOFFSET 0.00 2.00 0.00")
        lines.append("\t\t\t}")
        lines.append("\t\t}")
        lines.append("}")
        lines.append("MOTION")
        frames = len(motion_list)
        frame_time = 1.0/25.0
        lines.append(f"Frames: {frames}")
        lines.append(f"Frame Time: {frame_time:.6f}")
        for m in motion_list:
            # root pos (x y z) + zeros for rotations (we keep rotations zero for root)
            # approximate root pos using hip_y as small Y translate
            x = 0.0; y = m.get("hip_y",0.0); z = 0.0
            # neck rotations: Z Y X from motion (use neck_tilt, head_nod as rotation)
            neck_z = m.get("spine_bend",0.0)
            neck_y = m.get("neck_tilt",0.0)
            neck_x = m.get("head_nod",0.0)
            # neck child rotations zeros
            lines.append(f"{x:.6f} {y:.6f} {z:.6f} 0.0 0.0 0.0 {neck_z:.6f} {neck_y:.6f} {neck_x:.6f} 0.0 0.0 0.0")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            fh.write("\n".join(lines))
        return {"ok": True, "out": out_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ----------------------------
# 5) High-level pipeline
# ----------------------------
def run_voice2anim_pipeline(wav_path: str, profile: Dict | None = None, mode: str = "fast", out_name: str | None = None):
    tid = _task_id()
    out_name = out_name or f"v2a_{tid}.bvh"
    out_path = OUT / out_name
    if mode == "fast":
        feats = extract_audio_features(wav_path)
        if not feats.get("ok"):
            return feats
        pred = predict_motion_fast(feats, profile)
        if not pred.get("ok"):
            return pred
        # export bvh
        exp = export_bvh_simple(pred.get("motion", []), str(out_path))
        if not exp.get("ok"):
            return exp
        return {"ok": True, "task_id": tid, "bvh": str(out_path), "mode": "fast"}
    else:
        hq = predict_motion_hq(wav_path, out_npz=str(OUT / f"motion_{tid}.npz"))
        if not hq.get("ok"):
            return hq
        # extern model should output per-joint arrays — here we just pass NPZ through and user can retarget in Blender
        return {"ok": True, "task_id": tid, "motion_npz": hq.get("out")}
