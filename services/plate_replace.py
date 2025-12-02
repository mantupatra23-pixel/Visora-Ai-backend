# services/plate_replace.py
import subprocess, shlex, json
from pathlib import Path
import numpy as np
import cv2

def compute_homography(src_pts, dst_pts):
    src = np.array(src_pts, dtype=np.float32)
    dst = np.array(dst_pts, dtype=np.float32)
    H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return H

def warp_plate(plate_path, H, output_path, out_size):
    img = cv2.imread(plate_path)
    warped = cv2.warpPerspective(img, H, out_size)
    cv2.imwrite(output_path, warped)
    return output_path

def ffmpeg_overlay(bg_video, fg_video, out_video, x=0, y=0):
    cmd = f'ffmpeg -y -i "{bg_video}" -i "{fg_video}" -filter_complex "overlay={x}:{y}" -c:v libx264 -crf 18 -preset veryfast "{out_video}"'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode==0, res.stdout, res.stderr
