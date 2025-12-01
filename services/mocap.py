# services/mocap.py
"""
Motion Capture Engine wrapper
- Modes: "mediapipe" (fast, CPU-friendly), "movenet" (fast), "openpose" (high-quality, GPU)
- Functions:
    - save_upload(file_bytes, filename) -> path
    - extract_2d_keypoints(video_path, mode="mediapipe") -> json per-frame keypoints
    - smooth_keypoints(keypoints_seq, window=5) -> smoothed sequence
    - estimate_3d_from_2d(keypoints_seq, method="simple_lifting") -> 3D keypoints (basic)
    - export_bvh(keypoints_3d, skeleton_map, out_path) -> writes BVH
    - export_fbx(keypoints_3d, out_path) -> (optional) calls blender/FBX exporter or uses fbx SDK
Notes:
- Heavy ops should be delegated to Celery worker (not blocking).
- This file uses MediaPipe by default for immediate testing.
"""

import os, json, uuid, subprocess, tempfile, math
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

ROOT = Path(".").resolve()
UPLOADS = ROOT / "uploads" / "mocap"
OUTDIR = ROOT / "static" / "mocap"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

def _task_id():
    return uuid.uuid4().hex[:12]

def save_upload(file_bytes: bytes, filename: str | None = None) -> str:
    fname = filename or f"mocap_{_task_id()}.mp4"
    dest = UPLOADS / fname
    with open(dest, "wb") as f:
        f.write(file_bytes)
    return str(dest)

# ------------------------------
# 1) 2D keypoint extraction (MediaPipe)
# ------------------------------
def extract_2d_keypoints_mediapipe(video_path: str, max_frames: int = None) -> Dict:
    """
    Returns:
      { "fps": 30, "frames": [ {"time":0.0, "keypoints":[(x,y,score), ...]}, ... ] }
    Uses: mediapipe (python) -> install: pip install mediapipe opencv-python
    """
    try:
        import cv2
        import mediapipe as mp
    except Exception as e:
        return {"ok": False, "error": "mediapipe_not_installed", "msg": str(e)}

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        idx += 1
        if max_frames and idx > max_frames:
            break
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(img_rgb)
        kps = []
        if res.pose_landmarks:
            for lm in res.pose_landmarks.landmark:
                kps.append((lm.x, lm.y, lm.visibility if hasattr(lm,'visibility') else 1.0))
        else:
            # fill with zeros for consistent indexing (33 for mp pose)
            kps = [(0.0,0.0,0.0)] * 33
        frames.append({"time": round((idx-1)/fps, 6), "keypoints": kps})
    cap.release()
    pose.close()
    return {"ok": True, "fps": fps, "frames": frames}

# ------------------------------
# 2) Simple smoothing
# ------------------------------
def smooth_keypoints(frames: List[Dict], window: int = 5) -> List[Dict]:
    """
    frames: list of {"time":..., "keypoints":[(x,y,score), ...]}
    returns smoothed frames (same length)
    """
    arr = np.array([[[kp[0], kp[1], kp[2]] for kp in f["keypoints"]] for f in frames])  # shape (T, N, 3)
    pad = window//2
    padded = np.pad(arr, ((pad,pad),(0,0),(0,0)), mode='edge')
    out = []
    for i in range(arr.shape[0]):
        win = padded[i:i+window].mean(axis=0)
        kps = [(float(w[0]), float(w[1]), float(w[2])) for w in win]
        out.append({"time": frames[i]["time"], "keypoints": kps})
    return out

# ------------------------------
# 3) Basic 3D lifting (weak perspective assumption)
# ------------------------------
def lift_2d_to_3d_simple(frames: List[Dict], focal: float = 1.0, depth_scale: float = 1.0) -> List[Dict]:
    """
    Very naive lifting: estimate Z from relative keypoint size (not accurate).
    For production use: use a 3D pose model (VideoPose3D, SPIN).
    This returns list of frames with 3D coords per joint: (x,y,z)
    """
    out = []
    for f in frames:
        kps3 = []
        for (x,y,s) in f["keypoints"]:
            # map normalized x,y to centered coords
            cx = (x - 0.5)
            cy = (0.5 - y)
            z = (1.0 - s) * depth_scale  # lower visibility -> assume further
            kps3.append((cx, cy, z))
        out.append({"time": f["time"], "keypoints3d": kps3})
    return out

# ------------------------------
# 4) Export BVH (very generic skeleton mapping)
# ------------------------------
def export_bvh_from_3d(frames3d: List[Dict], out_path: str, skeleton_name: str = "human") -> Dict:
    """
    Export a simple BVH file approximating motion using hip as root.
    Note: This is a simplified BVH writer for quick preview. For production use retarget via Blender (fbx/bvh export there).
    """
    try:
        # very naive BVH: use joint 0 as root, and write positions as channels Xposition Yposition Zposition and rotations zero
        joints_count = len(frames3d[0]["keypoints3d"])
        # We'll create a single root with 0 rotation channels and write frame positions as root translation
        times = [f["time"] for f in frames3d]
        fps = round(1.0 / (times[1]-times[0])) if len(times)>1 else 25
        out_lines = []
        out_lines.append("HIERARCHY")
        out_lines.append("ROOT Hips")
        out_lines.append("{")
        out_lines.append("\tOFFSET 0.00 0.00 0.00")
        out_lines.append("\tCHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation")
        out_lines.append("\tEnd Site")
        out_lines.append("\t{")
        out_lines.append("\t\tOFFSET 0.00 0.00 0.00")
        out_lines.append("\t}")
        out_lines.append("}")
        out_lines.append("MOTION")
        out_lines.append(f"Frames: {len(frames3d)}")
        out_lines.append(f"Frame Time: {1.0/fps:.6f}")
        for f in frames3d:
            root = f["keypoints3d"][0]  # joint0 as hip
            x,y,z = root
            # rotations zero
            out_lines.append(f"{x:.6f} {y:.6f} {z:.6f} 0.0 0.0 0.0")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            fh.write("\n".join(out_lines))
        return {"ok": True, "out": str(out_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ------------------------------
# 5) High-level pipeline
# ------------------------------
def run_mocap_pipeline(video_path: str, mode: str = "mediapipe", smooth_w: int = 5, lift_method: str = "simple", out_name: str | None = None):
    """
    High-level: save upload -> extract 2D -> smooth -> lift to 3D -> export BVH
    Returns: {"ok":True, "bvh":"/path/to.bvh", "task_id":...}
    """
    tid = _task_id()
    out_name = out_name or f"mocap_{tid}.bvh"
    out_path = OUTDIR / out_name
    # 1) extract 2D
    if mode == "mediapipe":
        res = extract_2d_keypoints_mediapipe(video_path)
    else:
        # placeholder for other modes; user must implement OpenPose wrapper separately
        return {"ok": False, "error": "unsupported_mode", "supported": ["mediapipe"]}
    if not res.get("ok"):
        return res
    frames = res["frames"]
    # 2) smoothing
    frames_s = smooth_keypoints(frames, window=smooth_w)
    # 3) lift to 3d
    if lift_method == "simple":
        frames3d = lift_2d_to_3d_simple(frames_s)
    else:
        frames3d = lift_2d_to_3d_simple(frames_s)
    # 4) export BVH
    exp = export_bvh_from_3d(frames3d, str(out_path))
    if not exp.get("ok"):
        return exp
    return {"ok": True, "task_id": tid, "bvh": str(out_path), "fps": res.get("fps",25)}
