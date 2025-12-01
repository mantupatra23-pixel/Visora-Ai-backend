# services/chroma_helper.py
"""
Advanced chroma key compositing using OpenCV:
- create_matte(fg_path, key_color=(0,255,0), thresh=60, blur=3)
- spill_suppression(fg_bgr, matte)
- composite_over_background(fg_path, bg_path, out_path, key_color=(0,255,0))
Requires: opencv-python, numpy
pip install opencv-python numpy
"""
import cv2
import numpy as np
from pathlib import Path
import subprocess
import shlex
import tempfile
from services.visual_vfx import _run

def create_matte(img_bgr, key_color=(0,255,0), thresh=60, blur=3):
    # convert to HSV and compute distance from key color
    key_bgr = np.uint8([[list(key_color)]])
    key_hsv = cv2.cvtColor(key_bgr, cv2.COLOR_BGR2HSV)[0,0]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # distance in HSV space (hue difference and sat/value)
    dh = np.abs(hsv[:,:,0].astype(int) - int(key_hsv[0]))
    ds = np.abs(hsv[:,:,1].astype(int) - int(key_hsv[1]))
    dv = np.abs(hsv[:,:,2].astype(int) - int(key_hsv[2]))
    dist = dh*2 + ds*0.8 + dv*0.2
    matte = np.clip((dist > thresh).astype(np.uint8)*255, 0, 255)
    if blur>0:
        matte = cv2.GaussianBlur(matte, (blur|1, blur|1), 0)
    # normalize to 0..1 float matte
    matt_f = (matte.astype(np.float32)/255.0)
    return matt_f

def spill_suppression(img_bgr, matte, key_color=(0,255,0)):
    # reduce green channel where matte is low (i.e., where key existed)
    out = img_bgr.copy().astype(np.float32)
    key = np.array(key_color, dtype=np.float32)
    # compute desaturated version
    lum = 0.299*out[:,:,2] + 0.587*out[:,:,1] + 0.114*out[:,:,0]  # note BGR ordering
    # where matte < 0.5 (i.e., keyed region) reduce green channel proportionally
    mask = (1.0 - matte)  # 1 where key present
    # reduce green by factor
    out[:,:,1] = out[:,:,1] * (1.0 - 0.65*mask)
    # clip and convert back
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out

def composite_over_background(fg_path, bg_path, out_path, key_color=(0,255,0), thresh=60, blur=5):
    fg_path = Path(fg_path)
    bg_path = Path(bg_path)
    out_path = Path(out_path)
    if not fg_path.exists() or not bg_path.exists():
        return {"ok": False, "error": "file missing"}
    cap_fg = cv2.VideoCapture(str(fg_path))
    cap_bg = cv2.VideoCapture(str(bg_path))
    fps = cap_fg.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap_fg.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap_fg.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    tmp_out = str(out_path.with_suffix(".tmp.mp4"))
    writer = cv2.VideoWriter(tmp_out, fourcc, fps, (w,h))
    # iterate frames
    while True:
        ret1, frame_fg = cap_fg.read()
        ret2, frame_bg = cap_bg.read()
        if not ret1:
            break
        if not ret2:
            # loop background if shorter
            cap_bg.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret2, frame_bg = cap_bg.read()
            if not ret2:
                frame_bg = np.zeros_like(frame_fg)
        # resize background to match
        frame_bg = cv2.resize(frame_bg, (w,h))
        matte = create_matte(frame_fg, key_color=key_color, thresh=thresh, blur=blur)
        matte_3 = np.stack([matte, matte, matte], axis=2)
        fg_supp = spill_suppression(frame_fg, matte, key_color=key_color)
        comp = (fg_supp.astype(np.float32)*matte_3 + frame_bg.astype(np.float32)*(1.0-matte_3)).astype(np.uint8)
        writer.write(comp)
    writer.release()
    cap_fg.release()
    cap_bg.release()
    # optional remux audio from background (or fg)
    res = _run(f'ffmpeg -y -i "{tmp_out}" -i "{str(bg_path)}" -map 0:v -map 1:a? -c:v libx264 -c:a aac -shortest "{str(out_path)}"')
    # cleanup tmp
    try:
        Path(tmp_out).unlink()
    except Exception:
        pass
    return res
