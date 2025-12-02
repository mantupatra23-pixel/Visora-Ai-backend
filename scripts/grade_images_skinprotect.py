#!/usr/bin/env python3
"""
Apply LUT to images but protect skin regions (face-detection mask + smooth blending).
Usage:
  python3 scripts/grade_images_skinprotect.py --input in.png --output out.png --cube luts/teal_orange.cube
Or for folders:
  python3 scripts/grade_images_skinprotect.py --input frames/ --output out_frames/ --cube luts/teal_orange.cube
"""
import argparse, sys, cv2, numpy as np
from pathlib import Path
from scripts.grade_images import read_cube, apply_cube_to_image, apply_curve_exposure_contrast

def detect_face_mask(img_bgr, scaleFactor=1.1, minNeighbors=5, minSize=(30,30)):
    # uses OpenCV haarcascade (shipped with opencv)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    for (x,y,w,h) in faces:
        # expand bbox a bit to include cheeks/neck
        pad_w = int(w*0.25); pad_h = int(h*0.35)
        x0 = max(0, x-pad_w); y0 = max(0, y-pad_h)
        x1 = min(img_bgr.shape[1], x+w+pad_w); y1 = min(img_bgr.shape[0], y+h+pad_h)
        mask[y0:y1, x0:x1] = 255
    # smooth mask edges (gaussian blur)
    mask = cv2.GaussianBlur(mask, (51,51), 0)
    # normalize to 0..1 float mask
    mask_f = (mask.astype(np.float32)/255.0)[:,:,None]
    return mask_f

def blend_images(original_bgr, graded_bgr, mask_f):
    # mask_f: HxWx1 float 0..1 where 1 means protect (keep original), 0 means fully graded
    # we want to preserve skin (original) where mask==1; so result = original*mask + graded*(1-mask)
    res = (original_bgr.astype(np.float32) * mask_f + graded_bgr.astype(np.float32) * (1.0 - mask_f)).astype(np.uint8)
    return res

def process_file(inp, outp, cube=None, exposure=1.0, contrast=1.0):
    img = cv2.imread(str(inp))
    if img is None:
        raise RuntimeError(f"Cannot read {inp}")
    # detect mask
    mask = detect_face_mask(img)
    # apply cube LUT to whole image
    graded = img.copy()
    if cube:
        lut = read_cube(cube)
        graded = apply_cube_to_image(img, lut)
    # optional curve adjustments on graded
    graded = apply_curve_exposure_contrast(graded, exposure=exposure, contrast=contrast)
    # blend preserving skin
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
