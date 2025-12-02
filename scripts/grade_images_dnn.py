#!/usr/bin/env python3
# scripts/grade_images_dnn.py
"""
DNN-based face detection + skin-preserve grade.
Downloads lightweight OpenCV DNN model (res10_300x300_ssd) if not present.
Usage:
  python3 scripts/grade_images_dnn.py --input frames/ --output out_frames/ --cube assets/luts/teal_orange.cube
"""
import argparse, os, sys, cv2, numpy as np
from pathlib import Path
from scripts.grade_images import read_cube, apply_cube_to_image, apply_curve_exposure_contrast
import urllib.request, ssl

MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
PROTOTXT = MODEL_DIR / "deploy.prototxt"
CAFFEMODEL = MODEL_DIR / "res10_300x300_ssd_iter_140000.caffemodel"

# URLs (OpenCV hosted raw files) - code will try to download if missing
PROTOTXT_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
CAFFEMODEL_URL = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/master/res10_300x300_ssd_iter_140000_fp16.caffemodel"

def download_model():
    ctx = ssl.create_default_context()
    try:
        if not PROTOTXT.exists():
            print("Downloading prototxt...")
            urllib.request.urlretrieve(PROTOTXT_URL, str(PROTOTXT))
        if not CAFFEMODEL.exists():
            print("Downloading caffemodel (may be large)...")
            urllib.request.urlretrieve(CAFFEMODEL_URL, str(CAFFEMODEL))
    except Exception as e:
        print("Auto-download failed:", e)
        print("Please download manually and place in models/ folder.")
        raise

def detect_faces_dnn(img):
    # returns mask (H,W) float 0..1 where 1=face region
    if not (PROTOTXT.exists() and CAFFEMODEL.exists()):
        download_model()
    net = cv2.dnn.readNetFromCaffe(str(PROTOTXT), str(CAFFEMODEL))
    h,w = img.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(img, (300,300)), 1.0, (300,300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()
    mask = np.zeros((h,w), dtype=np.uint8)
    for i in range(detections.shape[2]):
        confidence = float(detections[0,0,i,2])
        if confidence > 0.5:
            box = detections[0,0,i,3:7] * np.array([w,h,w,h])
            (x1,y1,x2,y2) = box.astype("int")
            # expand box a bit
            pad_w = int((x2-x1)*0.25)
            pad_h = int((y2-y1)*0.35)
            x0 = max(0, x1-pad_w); y0 = max(0, y1-pad_h)
            x1 = min(w, x2+pad_w); y1 = min(h, y2+pad_h)
            mask[y0:y1,x0:x1] = 255
    # soften mask
    mask = cv2.GaussianBlur(mask, (81,81), 0)
    mask_f = (mask.astype(np.float32)/255.0)[:,:,None]
    return mask_f

def blend_images(original_bgr, graded_bgr, mask_f):
    res = (original_bgr.astype(np.float32) * mask_f + graded_bgr.astype(np.float32) * (1.0 - mask_f)).astype(np.uint8)
    return res

def process_file(inp, outp, cube=None, exposure=1.0, contrast=1.0):
    img = cv2.imread(str(inp))
    if img is None:
        raise RuntimeError(f"Cannot read {inp}")
    mask = detect_faces_dnn(img)
    graded = img.copy()
    if cube:
        lut = read_cube(cube)
        graded = apply_cube_to_image(img, lut)
    graded = apply_curve_exposure_contrast(graded, exposure=exposure, contrast=contrast)
    out = blend_images(img, graded, mask)
    cv2.imwrite(str(outp), out)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--cube", required=False)
    p.add_argument("--exposure", type=float, default=1.0)
    p.add_argument("--contrast", type=float, default=1.0)
    args = p.parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    if inp.is_dir():
        out.mkdir(parents=True, exist_ok=True)
        files = sorted([x for x in inp.iterdir() if x.suffix.lower() in [".png",".jpg",".jpeg"]])
        for f in files:
            process_file(f, out / f.name, cube=args.cube, exposure=args.exposure, contrast=args.contrast)
    else:
        if out.is_dir():
            outfile = out / inp.name
        else:
            outfile = out
        process_file(inp, outfile, cube=args.cube, exposure=args.exposure, contrast=args.contrast)

if __name__=="__main__":
    main()
